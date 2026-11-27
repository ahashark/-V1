# MAISON L'ATELIER LONDON — 英伦高定香氛品牌展示站 (`sxy.ink`)

参照 [Jo Malone London UK](https://www.jomalone.co.uk/) 视觉体系搭建的 **Python + Flask 静态站点生成与展示项目**，已内置自定义域名 `sxy.ink` 的 `CNAME` 配置与 GitHub Pages 自动部署工作流。

## 1. 本地开发与导出静态站点

- **本地动态预览**：
  ```powershell
  .\.venv\Scripts\python.exe app.py
  ```
- **重新生成 GitHub Pages 静态文件（输出至 `docs/`）**：
  每次修改 [seed.py](core/seed.py) 中的香氛数据或 `templates/` 模板后执行：
  ```powershell
  .\.venv\Scripts\python.exe build_static.py
  ```

## 2. GitHub Pages 与自定义域名 `sxy.ink` 配置说明

1. **推送代码至 GitHub 仓库 `main` 分支**。
2. **开启 GitHub Pages**：
   打开仓库 **Settings → Pages**：
   - 方式一（直接读取已构建目录）：**Source** 选择 `Deploy from a branch` → 分支选 `main`，目录选 `/docs`，点击 **Save**。
   - 方式二（自动构建）：**Source** 选择 `GitHub Actions`（每次推送 Python 代码会自动运行 `.github/workflows/deploy-pages.yml` 重新构建发布）。
3. **配置 `sxy.ink` 域名 DNS 解析**：
   在您的域名服务商（如阿里云/腾讯云/Cloudflare）控制台添加以下 **4 条 A 记录**（指向 GitHub Pages 官方 IP）：
   - 主机记录 `@` → `185.199.108.153`
   - 主机记录 `@` → `185.199.109.153`
   - 主机记录 `@` → `185.199.110.153`
   - 主机记录 `@` → `185.199.111.153`
   - （可选）主机记录 `www` → `CNAME` 记录指向 `<你的GitHub用户名>.github.io`
4. DNS 生效后，在仓库 **Settings → Pages** 勾选 **Enforce HTTPS**，即可通过 `https://sxy.ink` 访问。
