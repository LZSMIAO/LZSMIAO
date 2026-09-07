# Qoder 編程統計

1. 在 Qoder 安裝官方 `WakaTime.vscode-wakatime` 擴充套件。
2. 登入 https://wakatime.com/api-key 取得 API Key，在 Qoder 命令面板執行 `WakaTime: API Key` 並填入。
3. 在此倉庫 Settings → Secrets and variables → Actions 新增 `WAKATIME_API_KEY`，填入同一把密鑰。不要寫入 README 或 Git。
4. 正常編輯程式，確認 WakaTime Dashboard 收到活動。
5. 在 Actions → Update profile activity → Run workflow 執行一次。

之後每六小時更新一次（北京時間 02:23、08:23、14:23、20:23），GitHub 排程可能延遲。統計小卡最多展示四種語言及總時間；不展示專案名稱、檔案路徑、機器名稱或 AI 對話。資料範圍使用 Asia/Shanghai 時區，彙總包含今天的近七天。

尚未設定密鑰、資料計算中或 API 暫時不可用時保留既有內容。若有 API 錯誤，請查看 Actions 狀態。使用 GitHub 內建的 GITHUB_TOKEN 寫回，不需要個人存取權杖。

小卡只使用 WakaTime API 回傳的實際資料，不填入演示時長。

公開動態使用未登入的 GitHub public events API，只列兩筆，排除本個人主頁倉庫的自動更新；預設折疊。沒有資料時顯示真實空狀態。

贪吃蛇每天約北京時間 09:43 更新。Platane/snk 產生貢獻路徑，再由 scripts/smooth_snake.py 轉成連續 paced SVG 動畫，移除蛇身錯開起步的停頓並合併空白網格。尊重系統減少動態效果設定，該模式顯示靜態圖。

本地驗證：`python3 scripts/test_profile.py`。
