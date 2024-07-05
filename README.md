# Embedding-Free Transformer with Inference Spatial Reduction for Efficient Semantic Segmentation (ECCV 2024)


This repository contains the official Pytorch implementation of training & evaluation code and the pretrained models for ISR method and EDAFormer.


## Installation

For install and data preparation, please refer to the guidelines in MMSegmentation v0.13.0.

Other requirements:
```pip install timm==0.3.2```

An example (works for me): ```CUDA 11.1``` and  ```pytorch 1.8.0``` 

```
pip install torchvision==0.8.2
pip install timm==0.3.2
pip install mmcv-full==1.2.7
pip install opencv-python==4.5.1.48
cd EDAFormer && pip install -e . --user
```

## Evaluation
  
```local_configs/``` contains config files. In config files, increase the ```reduction_ratios``` of our backbone and ```reduction_ratios``` of our decoder to apply our ISR method. 

Example: evaluate ```EDAFormer-T``` on ```ADE20K```:

```
# Single-gpu testing
python tools/test.py local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file

# Multi-gpu testing
./tools/dist_test.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file <GPU_NUM>

# Multi-gpu, multi-scale testing
tools/dist_test.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file <GPU_NUM> --aug-test
```

## Training

Example: train ```EDAFormer-T``` on ```ADE20K```:

```
# Single-gpu training
python tools/train.py local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py 

# Multi-gpu training
./tools/dist_train.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py <GPU_NUM>
```
