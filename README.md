# LottoAI Daily V2

这是一个可以直接部署到 GitHub Pages 的手机端彩票数据研究站。

## 你会得到什么

- 手机浏览器直接打开
- 双色球 / 大乐透切换
- 最新开奖
- 近100期频次、遗漏、和值、奇偶统计
- 30,000 次候选组合搜索
- Top 6 候选
- GitHub Actions 每天自动拉取公开历史数据
- GitHub Pages 自动部署
- 可以“添加到手机主屏幕”，作为 PWA 使用

## 数据

默认使用 `yangxb919/lottery-data` 的公开 JSON；该仓库说明其数据源为 500.com 历史数据，并由 GitHub Actions 自动更新。正式开奖请以官方渠道核对。

## 部署到你自己的 GitHub

1. 新建公开仓库，例如 `lottoai`
2. 上传本项目全部文件
3. GitHub -> Settings -> Pages
4. Source 选择 `GitHub Actions`
5. Actions 页面手动运行 `Update data and deploy LottoAI`
6. 部署完成后会得到：
   `https://你的GitHub用户名.github.io/lottoai/`

GitHub Pages 官方支持通过 Actions 部署静态站点。

## 重要

当前 V2 是“静态可部署版”。它把分析计算放在浏览器里，因此无需后端服务器。
下一阶段可以继续加入：
- 真正的 walk-forward 回测
- 预测锁定/开奖后结算
- 历史预测档案
- 多模型投票
- 蒙特卡洛覆盖
- PWA 离线缓存
- 可选的 Telegram/邮件通知

本项目不承诺预测中奖，不构成购彩或投资建议。
