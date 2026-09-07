# Qoder 編程統計

1. 在 Qoder 安裝官方 `WakaTime.vscode-wakatime` 擴充套件。
2. 登入 https://wakatime.com/api-key 取得 API Key，在 Qoder 命令面板執行 `WakaTime: API Key` 並填入。
3. 在此倉庫 Settings → Secrets and variables → Actions 新增 `WAKATIME_API_KEY`，填入同一把密鑰。不要寫入 README 或 Git。
4. 正常編輯程式，確認 WakaTime Dashboard 收到活動。
5. 在 Actions → Update coding activity → Run workflow 執行一次。

之後每天約北京時間 09:23 更新，GitHub 排程可能延遲。頁面最多展示四種語言、兩個編輯器及總時間；不展示專案名稱、檔案路徑、機器名稱或 AI 對話。資料範圍與日期以 WakaTime 回傳結果為準，可在 WakaTime 帳號設定選擇 Asia/Shanghai 時區。

尚未設定密鑰、資料計算中或 API 暫時不可用時保留既有內容。若有 API 錯誤，請查看 Actions 狀態。使用 GitHub 內建的 GITHUB_TOKEN 寫回，不需要個人存取權杖。

WakaTime 只會從安裝並啟用後開始收集，不能補回過去未記錄的 Qoder 編輯時數。
