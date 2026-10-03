"""Small 2-D U-Net used for the controlled regional-vs-geometry loss ablation."""

from __future__ import annotations

try:
    import torch
    from torch import nn
    from torch.nn import functional as F
except ImportError:  # pragma: no cover - optional training dependency
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]


if torch is None:  # pragma: no cover - minimal installations do not train

    class SmallUNet:
        def __init__(self, *_: object, **__: object) -> None:
            raise RuntimeError("SmallUNet requires PyTorch; install `pip install -e '.[train]'`.")

else:

    class _DoubleConv(nn.Module):
        def __init__(self, in_channels: int, out_channels: int) -> None:
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )

        def forward(self, x: object) -> object:
            return self.block(x)


    class SmallUNet(nn.Module):
        """Compact U-Net; outputs unbounded logits, not pre-sigmoid probabilities."""

        def __init__(self, in_channels: int, base_channels: int = 24) -> None:
            super().__init__()
            if in_channels < 1 or base_channels < 4:
                raise ValueError("in_channels must be positive and base_channels at least 4")
            self.enc1 = _DoubleConv(in_channels, base_channels)
            self.enc2 = _DoubleConv(base_channels, base_channels * 2)
            self.bottleneck = _DoubleConv(base_channels * 2, base_channels * 4)
            self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
            self.dec2 = _DoubleConv(base_channels * 6, base_channels * 2)
            self.dec1 = _DoubleConv(base_channels * 3, base_channels)
            self.head = nn.Conv2d(base_channels, 1, kernel_size=1)

        @staticmethod
        def _up(x: object, reference: object) -> object:
            return F.interpolate(x, size=reference.shape[-2:], mode="bilinear", align_corners=False)

        def forward(self, x: object) -> object:
            e1 = self.enc1(x)
            e2 = self.enc2(self.pool(e1))
            b = self.bottleneck(self.pool(e2))
            d2 = self.dec2(torch.cat((self._up(b, e2), e2), dim=1))
            d1 = self.dec1(torch.cat((self._up(d2, e1), e1), dim=1))
            return self.head(d1)
