import torch, torchvision
print("torch      :", torch.__version__)
print("torchvision:", torchvision.__version__)
print("cuda avail :", torch.cuda.is_available())
print("device cnt :", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device 0   :", torch.cuda.get_device_name(0))
    print("capability :", torch.cuda.get_device_capability(0))
    x = torch.randn(2048, 2048, device="cuda")
    y = (x @ x).sum().item()
    print("matmul ok  :", abs(y) > 0)
    import torch.nn as nn
    m = nn.Sequential(nn.Linear(512, 512), nn.ReLU(), nn.Linear(512, 10)).cuda()
    m(torch.randn(128, 512, device="cuda")).sum().backward()
    print("cudnn/bwd  : OK")
