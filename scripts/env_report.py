"""Print interpreter + package versions + torch threading/CUDA status as JSON (run on the host via pump 'py' job)."""
import json, sys, platform, importlib
out = {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform()}
for m in ['numpy', 'scipy', 'pytest', 'PIL', 'matplotlib', 'pandas', 'torch']:
    try:
        x = importlib.import_module(m); out[m] = getattr(x, '__version__', '?')
    except Exception as e:
        out[m] = 'MISSING (%s)' % type(e).__name__
try:
    import torch
    out['torch_cuda_available'] = bool(torch.cuda.is_available()); out['torch_threads'] = torch.get_num_threads(); out['torch_build'] = torch.__config__.show()[:200].replace('\n', ' | ')
except Exception: pass
print(json.dumps(out, indent=1))
