"""MuJoCo Go2 kinematic sensor benchmark. ICP baseline, not FAST-LIVO2.

GT poses only position the simulated sensors and evaluate results. The ICP
estimator receives noisy scans and a constant-velocity initialization.
"""
import pathlib, json, time, math, xml.etree.ElementTree as ET
import numpy as np
import mujoco
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from PIL import Image

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'site'/'dist'/'data'; OUT.mkdir(parents=True,exist_ok=True)
RAW=ROOT/'datasets'/'go2_sim';RAW.mkdir(parents=True,exist_ok=True)
ASSET=ROOT/'assets'/'unitree_go2'
N=180; DT=.1
boxes=[('wall_n',[0,6,1.5],[8,.12,1.5],[.36,.43,.51]),('wall_s',[0,-6,1.5],[8,.12,1.5],[.36,.43,.51]),('wall_e',[8,0,1.5],[.12,6,1.5],[.4,.47,.55]),('wall_w',[-8,0,1.5],[.12,6,1.5],[.4,.47,.55]),('rack_a',[3.5,2.5,1.1],[.8,1.1,1.1],[.15,.57,.64]),('rack_b',[-3,2.5,.9],[1,.7,.9],[.84,.53,.25]),('crate',[3,-2,.45],[.65,.65,.45],[.67,.48,.33]),('column',[-3,-2,1.4],[.3,.3,1.4],[.64,.67,.7])]

def voxel(p,size=.07):
    _,i=np.unique(np.floor(p/size).astype(np.int32),axis=0,return_index=True)
    return p[np.sort(i)],np.sort(i)

def register(src,target,initial):
    tree=cKDTree(target); T=initial.copy()
    for _ in range(15):
        p=src@T[:3,:3].T+T[:3,3];dist,idx=tree.query(p,workers=1)
        good=dist<min(.4,np.quantile(dist,.85))
        if good.sum()<50: break
        a=p[good];b=target[idx[good]];ac=a.mean(0);bc=b.mean(0)
        u,s,vt=np.linalg.svd((a-ac).T@(b-bc));R=vt.T@u.T
        if np.linalg.det(R)<0:vt[-1]*=-1;R=vt.T@u.T
        tr=bc-R@ac;T[:3,:3]=R@T[:3,:3];T[:3,3]=R@T[:3,3]+tr
        if np.linalg.norm(tr)<1e-5 and np.linalg.norm(R-np.eye(3))<1e-5:break
    return T

def build():
    root=ET.parse(ASSET/'scene.xml').getroot();w=root.find('worldbody')
    for name,pos,size,color in boxes:ET.SubElement(w,'geom',name=name,type='box',pos=' '.join(map(str,pos)),size=' '.join(map(str,size)),rgba=' '.join(map(str,color+[1])),group='0')
    ET.SubElement(w,'geom',name='moving_object',type='box',size='.28 .28 .8',pos='0 0 .8',rgba='.9 .3 .3 1',group='1')
    ET.SubElement(root,'statistic',center='0 0 0',extent='10')
    ET.SubElement(root,'size',memory='32M')
    path=ASSET/'lab_scene.xml';ET.ElementTree(root).write(path)
    assets={str(p.relative_to(ASSET)).replace('\\','/'):p.read_bytes() for p in ASSET.rglob('*') if p.is_file()}
    robot_xml=ET.fromstring(assets['go2.xml']);robot_xml.find('compiler').set('usethread','false')
    assets['go2.xml']=ET.tostring(robot_xml)
    m=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'),assets);d=mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m,d,0)
    return m,d

def scan_scene():
    m,d=build(); renderer=mujoco.Renderer(m,height=240,width=320)
    az=np.linspace(-np.pi,np.pi,240,endpoint=False);el=np.deg2rad(np.linspace(-28,24,16));a,e=np.meshgrid(az,el)
    dirs=np.stack([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)],-1).reshape(-1,3)
    gid=np.zeros(1,dtype=np.int32);group=np.array([1,0,0,0,0,0],dtype=np.uint8)
    scans=[];truepoints=[];poses=[];colors=[];rgb_frames=[]
    # Smooth closed traversal, with a stationary initialization segment.
    angles=np.maximum(0,np.arange(N)-10)/(N-11)*2*np.pi
    for k,theta in enumerate(angles):
        x,y=1.8*np.cos(theta),1.5*np.sin(theta);yaw=theta+np.pi/2
        z=.52+.008*np.sin(theta*8);R=Rotation.from_euler('z',yaw).as_matrix();origin=np.array([x,y,z])
        d.qpos[:3]=[x,y,.32];d.qpos[3:7]=[np.cos(yaw/2),0,0,np.sin(yaw/2)]
        # Prescribed joint pose: this benchmark tests perception, not learned gait stability.
        for j in range(4):d.qpos[7+j*3:10+j*3]=[0,.8+.15*np.sin(theta*12+j%2*np.pi),-1.6]
        m.geom_pos[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'moving_object')]=[-.5,2*np.sin(theta),.8]
        mujoco.mj_forward(m,d)
        hits=[];cols=[]
        for ray in dirs:
            worldray=R@ray;distance=mujoco.mj_ray(m,d,origin,worldray,group,True,-1,gid)
            if .2<distance<20:
                hits.append(ray*distance);cols.append(m.geom_rgba[gid[0],:3])
        p=np.asarray(hits);scans.append(p);truepoints.append(p@R.T+origin);colors.append(np.array(cols))
        T=np.eye(4);T[:3,:3]=R;T[:3,3]=origin;poses.append(T)
        if k%15==0:
            cam=mujoco.MjvCamera();cam.type=mujoco.mjtCamera.mjCAMERA_FREE;cam.lookat[:]=[x+.9*np.cos(yaw),y+.9*np.sin(yaw),.5];cam.distance=.9;cam.azimuth=np.rad2deg(yaw);cam.elevation=0
            renderer.update_scene(d,camera=cam);rgb=renderer.render().copy();Image.fromarray(rgb).save(OUT/f'rgb-{k:03d}.jpg',quality=90);rgb_frames.append(k)
        if k==40:
            cam=mujoco.MjvCamera();cam.lookat[:]=[0,0,0];cam.distance=14;cam.azimuth=135;cam.elevation=-55
            renderer.update_scene(d,camera=cam);Image.fromarray(renderer.render()).save(OUT/'simulation.jpg')
        if k%30==0:print('sensor frame',k,flush=True)
    renderer.close()
    poses=np.array(poses);vel=np.gradient(poses[:,:3,3],DT,axis=0);acc=np.gradient(vel,DT,axis=0);omega=np.gradient(np.unwrap(angles),DT)
    imu=np.column_stack((np.arange(N)*DT,np.zeros(N),np.zeros(N),omega,np.einsum('nji,nj->ni',poses[:,:3,:3],acc+np.array([0,0,9.81]))))
    np.savez_compressed(RAW/'sensors.npz',poses=poses,imu=imu,**{f'scan_{i:03d}':s.astype('f4') for i,s in enumerate(scans)})
    np.savetxt(RAW/'imu.csv',imu,delimiter=',',header='t,gx,gy,gz,ax,ay,az')
    return scans,poses,truepoints,colors,rgb_frames

def main():
    start=time.time();scans,gt,reference,colors,rgb_frames=scan_scene();truth,_=voxel(np.concatenate(reference),.05);ref_tree=cKDTree(truth);results=[];runs=[]
    for seed in [17,42,91]:
        rng=np.random.default_rng(seed);est=[];maps=[];cols=[];timings=[];prior=np.eye(4)
        for i,clean in enumerate(scans):
            noisy=clean+rng.normal(0,.01,clean.shape);p,inds=voxel(noisy,.1);tic=time.perf_counter()
            if i==0:T=gt[0].copy()
            else:T=register(p,target,est[-1]@prior)
            if i:prior=np.linalg.inv(est[-1])@T
            est.append(T);target=p@T[:3,:3].T+T[:3,3];maps.append(target);cols.append(colors[i][inds]);timings.append(time.perf_counter()-tic)
        estimate=np.array(est);cloud=np.concatenate(maps);rgb=np.concatenate(cols);cloud,idx=voxel(cloud,.07);rgb=rgb[idx]
        error=np.linalg.norm(estimate[:,:3,3]-gt[:,:3,3],axis=1);dist=ref_tree.query(cloud,workers=1)[0];back=cKDTree(cloud).query(truth,workers=1)[0]
        re=np.linalg.inv(estimate[:-1])@estimate[1:];rg=np.linalg.inv(gt[:-1])@gt[1:];rpe=np.linalg.norm((np.linalg.inv(rg)@re)[:,:3,3],axis=1)
        metric={'seed':seed,'frames':N,'points':len(cloud),'ate_rmse_m':float(np.sqrt(np.mean(error**2))),'rpe_translation_rmse_m':float(np.sqrt(np.mean(rpe**2))),'map_mean_nn_m':float(dist.mean()),'map_p95_nn_m':float(np.quantile(dist,.95)),'observed_surface_coverage_10cm':float(np.mean(back<.1)),'icp_mean_ms':float(np.mean(timings[1:])*1000),'noise_std_m':.01,'alignment':'Initial pose fixed to ground truth; no post-hoc alignment','method':'scan-to-scan trimmed point-to-point ICP / constant-velocity initialization','imu_used_by_estimator':False,'rgb_used_by_estimator':False}
        results.append(metric);runs.append(estimate[:,:3,3].round(5).tolist());print(metric,flush=True)
        if seed==17:
            cloud.astype('<f4').tofile(OUT/'map-positions.bin');(rgb.clip(0,1)*255).astype('u1').tofile(OUT/'map-colors.bin')
            # Track acquisition order for progressive point-cloud playback.
            np.minimum(idx//max(1,len(np.concatenate(maps))//N),N-1).astype('<u2').tofile(OUT/'map-frame.bin')
            with open(OUT/'map.ply','w') as f:
                f.write(f'ply\nformat ascii 1.0\nelement vertex {len(cloud)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
                for q,c in zip(cloud,(rgb.clip(0,1)*255).astype('u1')):f.write(' '.join(map(str,[*q,*c]))+'\n')
    meta={'simulator':'MuJoCo '+mujoco.__version__,'robot':'Unitree Go2 / MuJoCo Menagerie','control':'Prescribed kinematic trajectory, not a locomotion policy or physical navigation test','sensors':{'lidar':'16 channels × 240 azimuth rays, 10 Hz, 1 cm independent XYZ noise','rgb':'320×240 preview; not fused by ICP baseline','imu':'Derived specific force and angular velocity exported; not fused by ICP baseline'},'dynamic_objects':'Moving box visible in RGB, excluded from LiDAR using simulator geometry group (oracle mask, not learned segmentation)','runs':results,'trajectory_gt':gt[:,:3,3].round(5).tolist(),'trajectory_est':runs,'yaw':np.unwrap(Rotation.from_matrix(gt[:,:3,:3]).as_euler('xyz')[:,2]).round(5).tolist(),'rgb_frames':rgb_frames,'boxes':[{'name':n,'position':p,'size':s,'color':c} for n,p,s,c in boxes],'duration_seconds':N*DT,'dt':DT,'seconds_to_generate':time.time()-start,'fast_livo2_executed':False,'point_color':'Simulator material color, not RGB projection or predicted semantics'}
    (OUT/'simulation.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));(ROOT/'reports'/'simulation.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));print('DONE',flush=True)
if __name__=='__main__':main()
