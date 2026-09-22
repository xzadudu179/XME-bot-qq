# cloudflared 配置同步

`config.yml` 是 `/etc/cloudflared/config.yml` 的**唯一来源**。bot 启动时（`bot_init.sync_cloudflared_ingress`）
会自动比对并同步，有变化才重启 cloudflared，所以改放行路径不用再手动开编辑器改 `/etc`。

## 一次性授权

写 `/etc` 和重启 cloudflared 需要 root，而 bot 以普通用户跑，因此要配一条 sudoers：

```bash
sudo bash deploy/cloudflared/install.sh
```

它只授权两条命令——把 `deploy/cloudflared/config.yml` 装到 `/etc/cloudflared/config.yml`、以及
`systemctl restart cloudflared`，不放开 root shell。内容由 `cloudflared_sync.sudoers_line()` 生成，
和 bot 实际调用的参数是同一处代码，不会对不上。

## 日常使用

1. 改 `deploy/cloudflared/config.yml`（加一条 `path` 或新域名）。
2. 重启 bot（watchdog 拉起即可），启动日志里会出现 `cloudflared 配置：已同步并重启 cloudflared`。

想不重启 bot 就生效，手动跑一次（用 bot 自己的 venv 解释器，系统 `python3` 是 3.8，跑不了本模块的语法）：

```bash
./venv/bin/python cloudflared_sync.py
```

同步逻辑：两份内容一致 → 什么都不做（不调用 sudo）；有变化 → 先 `cloudflared tunnel ingress validate`
校验，通过才安装并重启；校验不通过则保留线上配置并告警。本机没装 cloudflared 时整体跳过。
同步前会把线上那份留一份副本到 `config.before-sync.yml`（已 gitignore）。

## 回滚

```bash
sudo install -m 644 -o root -g root deploy/cloudflared/config.before-sync.yml /etc/cloudflared/config.yml
sudo systemctl restart cloudflared
```

## 注意事项

- `path` 是正则，写反斜杠时别用 YAML 双引号（`path: "^/docs\.md$"` 会报 `unknown escape character`），
  裸写或单引号都行。改完可以先本地验一遍，`--config` 要放在子命令前面：
  ```bash
  cloudflared --config deploy/cloudflared/config.yml tunnel ingress validate
  cloudflared --config deploy/cloudflared/config.yml tunnel ingress rule https://api.example.com/docs.md
  ```
- 这里就是公网暴露面的白名单，默认拒绝：没写进来的路径一律 404。**不要**改成"按 bot 已注册路由自动生成"——
  同一个 Quart app 上还挂着 `/ws`、`/api`、`/status`、`/static/*`，自动生成会把它们一起放上公网，
  白名单也会从默认拒绝变成默认放行。
- 别在 `/etc/cloudflared/config.yml` 上手改：下次 bot 启动会被这份仓库配置覆盖（要临时救急就先停掉
  自动同步，改完再把改动搬回仓库）。
- 这里管的是"哪些路径能进来"，和浏览器的跨域（CORS）是两件事：跨域白名单在
  `xme/plugins/server_app/cors.py`，浏览器里调用还要那边放行同一个域名。
- `~/.cloudflared/config.yml` 是旧副本，systemd 走的始终是 `/etc/cloudflared/config.yml`，改那份不生效。
