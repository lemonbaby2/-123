"""Run a real semantic segmentation checkpoint on MuJoCo RGB frames."""
import pathlib,json,time,hashlib
import numpy as np,torch
from PIL import Image
from transformers import SegformerImageProcessor,SegformerForSemanticSegmentation
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'site'/'dist'/'data';MODEL=ROOT/'models'/'segformer-b0'
torch.set_num_threads(4)
processor=SegformerImageProcessor.from_pretrained(str(MODEL),local_files_only=True)
model=SegformerForSemanticSegmentation.from_pretrained(str(MODEL),local_files_only=True,use_safetensors=True).eval()
palette=np.random.default_rng(41).integers(60,240,(150,3),dtype='uint8');records=[];runs=[]
with torch.inference_mode():
    for run in range(3):
        tic=time.perf_counter()
        for frame in [0,60,120]:
            image=Image.open(OUT/f'rgb-{frame:03d}.jpg').convert('RGB')
            inputs=processor(images=image,return_tensors='pt',size={'height':256,'width':256})
            logits=model(**inputs).logits
            logits=torch.nn.functional.interpolate(logits,size=(image.height,image.width),mode='bilinear',align_corners=False)
            conf,labels=torch.softmax(logits,dim=1).max(dim=1);label=labels[0].numpy();prob=conf[0].numpy()
            if run==0:
                np.save(OUT/f'semantic-{frame:03d}.npy',label.astype('uint8'))
                overlay=(np.asarray(image)*.4+palette[label]*.6).astype('uint8');Image.fromarray(overlay).save(OUT/f'semantic-{frame:03d}.jpg',quality=90)
                ids,counts=np.unique(label,return_counts=True);order=np.argsort(counts)[::-1][:6]
                records.append({'frame':frame,'mean_max_probability':float(prob.mean()),'top_labels':[{'id':int(ids[i]),'label':model.config.id2label[int(ids[i])],'pixel_fraction':float(counts[i]/label.size)} for i in order]})
        runs.append({'run':run+1,'images':3,'seconds':time.perf_counter()-tic});print(runs[-1],flush=True)
meta={'model':'nvidia/segformer-b0-finetuned-ade-512-512','source':'https://huggingface.co/nvidia/segformer-b0-finetuned-ade-512-512','device':'cpu','input_resolution':[256,256],'pretrained_training_resolution':[512,512],'runs':runs,'predictions':records,'weight_sha256':hashlib.sha256((MODEL/'model.safetensors').read_bytes()).hexdigest(),'scope':'Actual neural network predictions on synthetic RGB. Reduced inference resolution. No ground-truth semantic evaluation, no mIoU claim, not fused into localization or 3D map. Not a language foundation model.'}
(OUT/'semantics.json').write_text(json.dumps(meta,indent=2));(ROOT/'reports'/'semantics.json').write_text(json.dumps(meta,indent=2));print('DONE',flush=True)
