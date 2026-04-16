#!/usr/bin/env python3
"""
检测报告小程序码生成器
生成报告 HTML + JSON，推送到 GitHub Pages
调用微信 API 生成小程序码，微信扫码直接进入小程序查看报告
"""

import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_FILE = BASE_DIR / "config.json"
REPORTS_DIR.mkdir(exist_ok=True)


# ── 配置管理 ────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_github_config() -> tuple[str, str]:
    """确保 GitHub 用户名和仓库名已配置，否则交互式询问"""
    cfg = load_config()
    username = cfg.get("github_username", "").strip()
    repo     = cfg.get("github_repo", "").strip()

    if not username or not repo:
        print("\n─── 首次使用：配置 GitHub Pages ───")
        if not username:
            username = input("  GitHub 用户名: ").strip()
        if not repo:
            repo = input("  GitHub 仓库名 (如 qr-report-generator): ").strip()
        cfg["github_username"] = username
        cfg["github_repo"]     = repo
        save_config(cfg)
        print("  已保存配置到 config.json\n")

    return username, repo


def ensure_wechat_config() -> tuple[str, str]:
    """确保微信小程序 AppID 和 AppSecret 已配置，否则交互式询问"""
    cfg       = load_config()
    app_id     = cfg.get("app_id", "").strip()
    app_secret = cfg.get("app_secret", "").strip()

    if not app_id or not app_secret:
        print("\n─── 配置微信小程序 ───")
        print("AppID 和 AppSecret 在微信公众平台 → 开发管理 → 开发设置 中获取\n")
        if not app_id:
            app_id = input("  小程序 AppID: ").strip()
        if not app_secret:
            app_secret = input("  小程序 AppSecret: ").strip()
        cfg["app_id"]     = app_id
        cfg["app_secret"] = app_secret
        save_config(cfg)
        print("  已保存配置到 config.json\n")

    return app_id, app_secret


# ── 交互输入 ────────────────────────────────────────────

def prompt(label: str, default: str = "") -> str:
    hint  = f" [{default}]" if default else ""
    value = input(f"  {label}{hint}: ").strip()
    return value if value else default


def collect_params() -> dict:
    print("\n" + "=" * 50)
    print("    检测报告二维码生成器")
    print("=" * 50)
    print("请依次填写报告信息（直接回车使用默认值）：\n")

    today = datetime.now().strftime("%Y/%m/%d")

    return {
        "report_id":   prompt("报告编号", "WJIST20250620040DDX"),
        "language":    prompt("报告语言", "中文"),
        "company":     prompt("委托单位", "大地熊（苏州）磁铁有限公司"),
        "report_date": prompt("报告时间", today),
    }


# ── HTML 生成 ────────────────────────────────────────────

def generate_html(params: dict) -> Path:
    report_id   = params["report_id"]
    language    = params["language"]
    company     = params["company"]
    report_date = params["report_date"]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>检测报告验证 - {report_id}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                   "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(160deg, #dce8f5 0%, #c8d8ec 100%);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 0 0 60px;
    }}

    .nav-bar {{
      width: 100%;
      max-width: 480px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px 20px 10px;
      position: relative;
    }}
    .nav-title {{
      font-size: 18px;
      font-weight: 600;
      color: #1a1a1a;
      text-align: center;
    }}
    .nav-subtitle {{
      font-size: 12px;
      color: #888;
      text-align: center;
      margin-top: 2px;
    }}
    .nav-close {{
      position: absolute;
      left: 20px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 22px;
      color: #555;
      line-height: 1;
    }}

    .card {{
      width: calc(100% - 28px);
      max-width: 460px;
      background: #fff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.10);
      margin-top: 12px;
    }}

    .card-header {{
      background: linear-gradient(135deg, #4a90d9 0%, #6c4fd0 100%);
      padding: 20px 24px;
      text-align: center;
    }}
    .card-header h1 {{
      color: #fff;
      font-size: 19px;
      font-weight: 700;
      line-height: 1.4;
      letter-spacing: 0.5px;
    }}

    .result-section {{
      padding: 28px 24px 20px;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .bracket {{
      flex-shrink: 0;
      width: 8px;
      height: 80px;
      border: 3px solid #2db55d;
      border-right: none;
      border-radius: 6px 0 0 6px;
    }}
    .result-content {{ flex: 1; }}
    .result-label {{
      font-size: 15px;
      color: #444;
      margin-bottom: 12px;
    }}
    .result-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, #2db55d, #22a350);
      color: #fff;
      font-size: 15px;
      font-weight: 600;
      padding: 8px 22px;
      border-radius: 50px;
      box-shadow: 0 3px 10px rgba(34,163,80,0.35);
    }}

    .divider {{
      height: 1px;
      background: #f0f0f0;
      margin: 0 24px;
    }}

    .info-list {{ padding: 8px 24px 28px; }}
    .info-row {{
      display: flex;
      align-items: baseline;
      padding: 16px 0;
      border-bottom: 1px solid #f3f3f3;
      gap: 12px;
    }}
    .info-row:last-child {{ border-bottom: none; }}
    .info-key {{
      flex-shrink: 0;
      width: 80px;
      font-size: 14px;
      color: #888;
      white-space: nowrap;
    }}
    .info-val {{
      font-size: 15px;
      color: #1a1a1a;
      font-weight: 500;
      word-break: break-all;
    }}
  </style>
</head>
<body>

  <div class="nav-bar">
    <span class="nav-close">✕</span>
    <div>
      <div class="nav-title">检测报告验证</div>
      <div class="nav-subtitle">report-verify</div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <h1>创标检测报告真伪查询验证</h1>
    </div>

    <div class="result-section">
      <div class="bracket"></div>
      <div class="result-content">
        <div class="result-label">报告查询结果：</div>
        <div class="result-badge">✓ 报告有效</div>
      </div>
    </div>

    <div class="divider"></div>

    <div class="info-list">
      <div class="info-row">
        <span class="info-key">报告编号：</span>
        <span class="info-val">{report_id}</span>
      </div>
      <div class="info-row">
        <span class="info-key">报告语言：</span>
        <span class="info-val">{language}</span>
      </div>
      <div class="info-row">
        <span class="info-key">委托单位：</span>
        <span class="info-val">{company}</span>
      </div>
      <div class="info-row">
        <span class="info-key">报告时间：</span>
        <span class="info-val">{report_date}</span>
      </div>
    </div>
  </div>

</body>
</html>
"""

    html_path = REPORTS_DIR / f"{report_id}.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


# ── JSON 生成（供小程序读取）─────────────────────────────

def generate_json(params: dict) -> Path:
    """将报告参数序列化为 JSON，部署到 GitHub Pages 后小程序通过 report_id 拉取"""
    report_id = params["report_id"]
    json_path = REPORTS_DIR / f"{report_id}.json"
    json_path.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


# ── 微信小程序码生成 ─────────────────────────────────────

def _get_access_token(app_id: str, app_secret: str) -> str:
    """用 AppID + AppSecret 换取微信接口调用凭证 access_token（有效期 2 小时）"""
    resp = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": app_id, "secret": app_secret},
        timeout=15,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"获取 access_token 失败：{data.get('errmsg', data)}")
    return data["access_token"]


def generate_miniprogram_qr(report_id: str, app_id: str, app_secret: str) -> Path:
    """
    调用 wxacode.getUnlimited 生成小程序码
    scene = report_id（≤32字节），小程序落地页为 pages/report/index
    官方文档：https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/qrcode-link/qr-code/getUnlimitedQRCode.html
    """
    if len(report_id.encode("utf-8")) > 32:
        raise ValueError(f"report_id 超过 32 字节限制，当前 {len(report_id.encode())} 字节")

    access_token = _get_access_token(app_id, app_secret)

    # env_version: release=正式版 / trial=体验版 / develop=开发版
    resp = requests.post(
        f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={access_token}",
        json={
            "scene":       report_id,
            "page":        "pages/report/index",
            "env_version": "trial",
            "width":       280,
        },
        timeout=15,
    )

    # 微信返回 JSON 时代表出错（正常返回二进制图片）
    if "application/json" in resp.headers.get("Content-Type", ""):
        raise RuntimeError(f"生成小程序码失败：{resp.json()}")

    qr_path = REPORTS_DIR / f"{report_id}_qr.png"
    qr_path.write_bytes(resp.content)
    return qr_path


# ── Git 自动推送 ──────────────────────────────────────────

def git_push(report_id: str) -> bool:
    """将新生成的报告文件（HTML + JSON + 小程序码）commit 并 push 到 GitHub"""
    candidates = [
        f"reports/{report_id}.html",
        f"reports/{report_id}.json",
        f"reports/{report_id}_qr.png",
    ]
    # 只添加实际存在的文件，小程序码生成失败时不阻塞推送
    files = [f for f in candidates if (BASE_DIR / f).exists()]
    cmds = [
        ["git", "add"] + files,
        ["git", "commit", "-m", f"add report {report_id}"],
        ["git", "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [!] 命令失败: {' '.join(cmd)}")
            print(f"      {result.stderr.strip()}")
            return False
    return True


# ── 主流程 ───────────────────────────────────────────────

def main():
    username, repo = ensure_github_config()
    app_id, app_secret = ensure_wechat_config()
    params    = collect_params()
    report_id = params["report_id"]

    print()

    # 1. 生成 HTML（备用网页入口）
    generate_html(params)
    print(f"[✓] HTML 已生成：reports/{report_id}.html")

    # 2. 生成 JSON（小程序扫码后拉取报告数据）
    generate_json(params)
    print(f"[✓] JSON 已生成：reports/{report_id}.json")

    # 3. 生成小程序码（调用微信 API）
    print("    正在调用微信 API 生成小程序码...")
    try:
        generate_miniprogram_qr(report_id, app_id, app_secret)
        print(f"[✓] 小程序码已生成：reports/{report_id}_qr.png")
    except Exception as e:
        print(f"[!] 小程序码生成失败：{e}")
        print("    请确认 AppID/AppSecret 正确，且小程序已发布（正式版/体验版）")

    # 4. 询问是否自动推送（JSON 推上去后小程序才能读到数据）
    print()
    choice = input("  是否立即 git push 到 GitHub？(y/N): ").strip().lower()
    if choice == "y":
        print("  正在推送...")
        if git_push(report_id):
            # 自定义域名（CNAME = ziping.site.a）时不需要 /{repo} 路径前缀
            pages_url = f"https://ziping.site/reports/{report_id}.json"
            print(f"  [✓] 推送成功！约 1 分钟后小程序可读取：")
            print(f"      {pages_url}")
        else:
            print("  [!] 推送失败，请手动执行：")
            print(f"      git add reports/{report_id}.html reports/{report_id}.json reports/{report_id}_qr.png")
            print(f"      git commit -m 'add report {report_id}'")
            print(f"      git push")
    else:
        print("\n  手动推送命令：")
        print(f"    git add reports/{report_id}.html reports/{report_id}.json reports/{report_id}_qr.png")
        print(f"    git commit -m 'add report {report_id}'")
        print(f"    git push")

    print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()
