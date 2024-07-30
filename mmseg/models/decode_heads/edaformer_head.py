# ---------------------------------------------------------------
# Copyright (c) 2021, NVIDIA Corporation. All rights reserved.
#
# This work is licensed under the NVIDIA Source Code License
# ---------------------------------------------------------------
import numpy as np
import torch.nn as nn
import torch
from mmcv.cnn import ConvModule, DepthwiseSeparableConvModule
from collections import OrderedDict

from mmseg.ops import resize
from ..builder import HEADS
from .decode_head import BaseDecodeHead
from mmseg.models.utils import *

import math
from timm.models.layers import DropPath, trunc_normal_


class DWConv(nn.Module):
    def __init__(self, dim=768):
        super(DWConv, self).__init__()
        self.dwconv = nn.Conv2d(dim, dim, 3, 1, 1, bias=True, groups=dim)

    def forward(self, x, H, W):
        B, N, C = x.shape
        x = x.transpose(1, 2).view(B, C, H, W)
        x = self.dwconv(x)
        x = x.flatten(2).transpose(1, 2)

        return x


class Mlp(nn.Module):
    def __init__(self, in_features, hidden_features=None, out_features=None, act_layer=nn.GELU, drop=0.):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.dwconv = DWConv(hidden_features)
        self.act = act_layer()
        self.fc2 = nn.Linear(hidden_features, out_features)
        self.drop = nn.Dropout(drop)
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            trunc_normal_(m.weight, std=.02)
            if isinstance(m, nn.Linear) and m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)
        elif isinstance(m, nn.Conv2d):
            fan_out = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
            fan_out //= m.groups
            m.weight.data.normal_(0, math.sqrt(2.0 / fan_out))
            if m.bias is not None:
                m.bias.data.zero_()

    def forward(self, x, H, W):
        x = self.fc1(x)
        x = self.dwconv(x, H, W)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.drop(x)
        return x


class Attention(nn.Module):
    def __init__(self, dim1, num_heads=8, qkv_bias=False, qk_scale=None, attn_drop=0., proj_drop=0., pool_ratio=16):
        super().__init__()
        assert dim1 % num_heads == 0, f"dim {dim1} should be divided by num_heads {num_heads}."

        self.dim1 = dim1
        self.pool_ratio = pool_ratio
        self.num_heads = num_heads
        head_dim = dim1 // num_heads

        self.scale = qk_scale or head_dim ** -0.5
       
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim1, dim1)
        self.proj_drop = nn.Dropout(proj_drop)

        self.pool = nn.AvgPool2d(pool_ratio, pool_ratio)
        self.sr = nn.Conv2d(dim1, dim1, kernel_size=1, stride=1)
        self.norm = nn.LayerNorm(dim1)
        self.act = nn.GELU()

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            trunc_normal_(m.weight, std=.02)
            if isinstance(m, nn.Linear) and m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)
        elif isinstance(m, nn.Conv2d):
            fan_out = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
            fan_out //= m.groups
            m.weight.data.normal_(0, math.sqrt(2.0 / fan_out))
            if m.bias is not None:
                m.bias.data.zero_()

    def forward(self, x, h, w):
        B, N, C = x.shape
        
        q = x.reshape(B, N, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)
        x_ = x.permute(0, 2, 1).reshape(B, C, h, w)
        x_ = self.sr(self.pool(x_)).reshape(B, C, -1).permute(0, 2, 1)
        x_ = self.norm(x_)
        x_ = self.act(x_)
        
        B1,N1,C1 = x_.shape
        k = x_.reshape(B, N1, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)
        v = x_.reshape(B, N1, self.num_heads, C // self.num_heads).permute(0, 2, 1, 3)

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        return x


class Block(nn.Module):

    def __init__(self, dim1, num_heads, mlp_ratio=4., qkv_bias=False, qk_scale=None, drop=0., attn_drop=0.,
                 drop_path=0., act_layer=nn.GELU, norm_layer=nn.LayerNorm, pool_ratio=16):
        super().__init__()
        self.norm1 = norm_layer(dim1)
        self.norm2 = norm_layer(dim1)


        self.attn = Attention(dim1=dim1, num_heads=num_heads, pool_ratio=pool_ratio)

        # NOTE: drop path for stochastic depth, we shall see if this is better than dropout here
        self.drop_path = DropPath(drop_path) if drop_path > 0. else nn.Identity()
        mlp_hidden_dim = int(dim1 * mlp_ratio)
        self.mlp = Mlp(in_features=dim1, hidden_features=mlp_hidden_dim, act_layer=act_layer, drop=drop)

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            trunc_normal_(m.weight, std=.02)
            if isinstance(m, nn.Linear) and m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)
        elif isinstance(m, nn.Conv2d):
            fan_out = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
            fan_out //= m.groups
            m.weight.data.normal_(0, math.sqrt(2.0 / fan_out))
            if m.bias is not None:
                m.bias.data.zero_()

    def forward(self, x, h, w):
        x = x + self.drop_path(self.attn(self.norm1(x), h, w))
        x = x + self.drop_path(self.mlp(self.norm2(x), h, w))

        return x


@HEADS.register_module()
class EDAFormerHead(BaseDecodeHead):
    def __init__(self, reduction_ratios, mlp_ratio, **kwargs):
        super(EDAFormerHead, self).__init__(input_transform='multiple_select', **kwargs)

        c2_in_channels, c3_in_channels, c4_in_channels = self.in_channels

        decoder_params = kwargs['decoder_params']
        embedding_dim = decoder_params['embed_dim']

        mlp_ratio = mlp_ratio

        self.attn4 = Block(dim1=c4_in_channels, num_heads=8, mlp_ratio=mlp_ratio, drop_path=0.1, pool_ratio=reduction_ratios[2])
        self.attn44 = Block(dim1=c4_in_channels, num_heads=8, mlp_ratio=mlp_ratio, drop_path=0.1, pool_ratio=reduction_ratios[2])
        self.attn444 = Block(dim1=c4_in_channels, num_heads=8, mlp_ratio=mlp_ratio, drop_path=0.1, pool_ratio=reduction_ratios[2])

        self.attn3 = Block(dim1=c3_in_channels, num_heads=4, mlp_ratio=mlp_ratio, drop_path=0.1, pool_ratio=reduction_ratios[1]*2)
        self.attn33 = Block(dim1=c3_in_channels, num_heads=4, mlp_ratio=mlp_ratio, drop_path=0.1, pool_ratio=reduction_ratios[1]*2)

        self.attn2 = Block(dim1=c2_in_channels, num_heads=2, mlp_ratio=mlp_ratio, drop_path=0.1, pool_ratio=reduction_ratios[0]*4)

        self.linear_fuse = ConvModule(
            in_channels=(c2_in_channels + c3_in_channels + c4_in_channels),
            out_channels=embedding_dim,
            kernel_size=1,
            norm_cfg=dict(type='SyncBN', requires_grad=True)
        )

        self.linear_pred = nn.Conv2d(embedding_dim, self.num_classes, kernel_size=1)

    def forward(self, inputs):
        x = self._transform_inputs(inputs)
        c2, c3, c4 = x

        n, _, h4, w4 = c4.shape
        _, _, h3, w3 = c3.shape
        _, _, h2, w2 = c2.shape

        c2 = c2.flatten(2).transpose(1, 2)
        c3 = c3.flatten(2).transpose(1, 2)
        c4 = c4.flatten(2).transpose(1, 2)

        _c4 = self.attn4(c4, h4, w4)
        _c4 = self.attn44(_c4, h4, w4)
        _c4 = self.attn444(_c4, h4, w4)
        _c4 = _c4.permute(0, 2, 1).reshape(n, -1, h4, w4)
        _c4 = resize(_c4, size=(h2, w2), mode='bilinear', align_corners=False)

        _c3 = self.attn3(c3, h3, w3)
        _c3 = self.attn33(_c3, h3, w3)
        _c3 = _c3.permute(0, 2, 1).reshape(n, -1, h3, w3)
        _c3 = resize(_c3, size=(h2, w2), mode='bilinear', align_corners=False)

        _c2 = self.attn2(c2, h2, w2)
        _c2 = _c2.permute(0, 2, 1).reshape(n, -1, h2, w2)

        _c = self.linear_fuse(torch.cat([_c4, _c3, _c2], dim=1))
        x = self.dropout(_c)

        x = self.linear_pred(x)
        
        return x