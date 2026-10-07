"""CloakBrowser 集成 (v317) — 深层浏览器指纹隐藏。

CloakBrowser 提供比标准 Playwright Stealth 更深层的指纹伪装:
- WebGL 渲染器/供应商伪装
- Canvas 像素噪声注入
- AudioContext 指纹修改
- Navigator.platform/hardwareConcurrency/deviceMemory 覆盖
- 字体列表伪装
- Screen 分辨率随机化

集成方式: 在 Playwright page 上注入 CDP 脚本，与现有 stealth_config.py 叠加使用。
"""
from __future__ import annotations

import random
import json
from typing import Any
from loguru import logger


# ─── WebGL 指纹伪装 ─────────────────────────────────────────
WEBGL_FINGERPRINT_SCRIPT = """
(() => {
    const vendors = ['Intel Inc.', 'Google Inc.', 'Mozilla', 'Apple Inc.'];
    const renderers = [
        'Intel Iris OpenGL Engine',
        'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)',
        'Mali-G72',
        'Adreno (TM) 640',
    ];
    const vendor = vendors[%(vendor_idx)d];
    const renderer = renderers[%(renderer_idx)d];

    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return vendor;   // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return renderer;  // UNMASKED_RENDERER_WEBGL
        return getParameter.call(this, param);
    };

    if (typeof WebGL2RenderingContext !== 'undefined') {
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return vendor;
            if (param === 37446) return renderer;
            return getParameter2.call(this, param);
        };
    }
})();
""" % {
    "vendor_idx": random.randint(0, 3),
    "renderer_idx": random.randint(0, 3),
}


# ─── Canvas 噪声注入 ───────────────────────────────────────
CANVAS_NOISE_SCRIPT = """
(() => {
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const w = this.width, h = this.height;
            if (w > 0 && h > 0) {
                try {
                    const imageData = ctx.getImageData(0, 0, w, h);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        // Tiny random noise on each pixel
                        const noise = (Math.random() - 0.5) * 2;
                        imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                    }
                    ctx.putImageData(imageData, 0, 0);
                } catch (e) {}
            }
        }
        return origToDataURL.apply(this, arguments);
    };
})();
"""


# ─── AudioContext 指纹修改 ─────────────────────────────────
AUDIO_FINGERPRINT_SCRIPT = """
(() => {
    const context = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (context) {
        const orig = context.prototype.getChannelData;
        context.prototype.getChannelData = function() {
            const result = orig.apply(this, arguments);
            // Add tiny random noise to audio fingerprint
            for (let i = 0; i < result.length; i += 100) {
                result[i] = result[i] + (Math.random() - 0.5) * 0.0001;
            }
            return result;
        };
    }
})();
"""


# ─── Navigator 属性覆盖 ────────────────────────────────────
NAVIGATOR_OVERRIDE_SCRIPT = """
(() => {
    // hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => %(cores)d
    });
    // deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => %(memory)d
    });
    // platform
    Object.defineProperty(navigator, 'platform', {
        get: () => '%(platform)s'
    });
    // maxTouchPoints
    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => %(touch)d
    });
})();
""" % {
    "cores": random.choice([4, 8, 12, 16]),
    "memory": random.choice([4, 8, 16]),
    "platform": random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
    "touch": random.choice([0, 1, 5, 10]),
}


# ─── Screen 分辨率随机化 ───────────────────────────────────
SCREEN_RANDOMIZE_SCRIPT = """
(() => {
    const screens = [
        {w: 1920, h: 1080}, {w: 1366, h: 768}, {w: 1536, h: 864},
        {w: 1440, h: 900}, {w: 2560, h: 1440}, {w: 1280, h: 720},
    ];
    const s = screens[%(idx)d];
    Object.defineProperty(screen, 'width', {get: () => s.w});
    Object.defineProperty(screen, 'height', {get: () => s.h});
    Object.defineProperty(screen, 'availWidth', {get: () => s.w});
    Object.defineProperty(screen, 'availHeight', {get: () => s.h - 40});
    Object.defineProperty(screen, 'colorDepth', {get: () => 24});
})();
""" % {"idx": random.randint(0, 5)}


# ─── 字体列表伪装 ──────────────────────────────────────────
FONT_FINGERPRINT_SCRIPT = """
(() => {
    const fakeFonts = [
        'Arial', 'Helvetica', 'Times New Roman', 'Georgia',
        'Courier New', 'Verdana', 'Trebuchet MS', 'Impact',
        'Comic Sans MS', 'Microsoft YaHei', 'SimSun', 'SimHei',
    ];
    if (window.document && document.fonts) {
        const origCheck = document.fonts.check;
        document.fonts.check = function(font, text) {
            return true;  // Always report font as available
        };
    }
})();
"""


# ─── 主函数: 应用所有 CloakBrowser 注入 ───────────────────
ALL_CLOAK_SCRIPTS = [
    ("webgl_fingerprint", WEBGL_FINGERPRINT_SCRIPT),
    ("canvas_noise", CANVAS_NOISE_SCRIPT),
    ("audio_fingerprint", AUDIO_FINGERPRINT_SCRIPT),
    ("navigator_override", NAVIGATOR_OVERRIDE_SCRIPT),
    ("screen_randomize", SCREEN_RANDOMIZE_SCRIPT),
    ("font_fingerprint", FONT_FINGERPRINT_SCRIPT),
]


def apply_cloak_browser(page) -> None:
    """Apply all CloakBrowser fingerprint cloaking scripts to a Playwright page.

    This should be called in addition to the standard stealth_config.py
    for maximum anti-detection coverage.

    Args:
        page: Playwright Page object
    """
    for name, script in ALL_CLOAK_SCRIPTS:
        try:
            # Inject via CDP (most reliable for early injection)
            client = page.context.new_cdp_session(page)
            client.send("Page.addScriptToEvaluateOnNewDocument", {"source": script})
            logger.debug(f"cloak_browser: injected {name}")
        except Exception as e:
            # Fallback: direct evaluate
            try:
                page.evaluate(script)
                logger.debug(f"cloak_browser: evaluated {name}")
            except Exception:
                logger.warning(f"cloak_browser: failed {name}: {e!r}")


def get_cloak_fingerprint() -> dict:
    """Return a summary of the current random fingerprint config."""
    return {
        "webgl_vendor_idx": random.randint(0, 3),
        "webgl_renderer_idx": random.randint(0, 3),
        "navigator_cores": random.choice([4, 8, 12, 16]),
        "navigator_memory": random.choice([4, 8, 16]),
        "navigator_platform": random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
        "screen_idx": random.randint(0, 5),
        "scripts_count": len(ALL_CLOAK_SCRIPTS),
    }
