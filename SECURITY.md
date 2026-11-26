# Безопасность

## Как сообщить об уязвимости

Сообщите о ней закрыто через GitHub: вкладка репозитория **Security** → **Report a vulnerability**. Не открывайте для
этого публичную задачу. Мы отвечаем в течение недели и благодарим вас в описании выпуска, если вы не против.

Исправления получает только последняя версия; обновляйтесь из окна SMTV, когда оно предложит новую версию.

## Что SMTV защищает — простыми словами

- **Ваши ключи** от сервисов нейросетей остаются на вашем компьютере — в системном хранилище паролей или в
  зашифрованном файле в папке SMTV — и уходят только тому сервису, которому принадлежат. Они никогда не появляются в
  окне, логах и отчётах о проблемах.
- **Страница SMTV** отвечает только на этом компьютере, и каждый запрос к ней требует секрета, который есть только у
  окна и страницы самого SMTV: другая программа или сайт не может управлять SMTV от вашего имени. Даже сама страница
  открывается только из SMTV (его значок или команда `smtv`), так что другой пользователь этого компьютера этот
  секрет не получит.
- **Телефон** видит SMTV, только когда вы это включили («Настройки → Телефон») и навели камеру на QR-код с новым
  случайным секретом; выключение сразу отключает все телефоны. С телефона нельзя увидеть или поменять ключи, обновить
  или удалить SMTV; аккаунт там только показывается — вход, выход и оплата происходят на компьютере.
- **Ссылку** на запись скачивает программа yt-dlp прямо на ваш компьютер, если вы включили «Скачивать ссылки самому».
  Когда откроется аккаунт StreamMoment, ссылка сможет идти и через его сервер: он передаёт запись в SMTV и ничего у
  себя не хранит. Ваш собственный файл никуда не отправляется. Текст стрима уходит только в выбранную вами нейросеть.
- **Обновления** приходят только из списка выпусков, подписанного авторами SMTV; SMTV проверяет подпись, никогда не
  возвращается к более старому списку и ставит только файлы, чьи контрольные суммы совпадают с этим списком.
- **Исправления**, которые предлагает SMTV (например, установка ffmpeg), запускают программу, которую SMTV сам знает
  для вашей системы, и показывают её до запуска; SMTV никогда не выполняет команду, полученную из интернета.

От чего SMTV не защищает: программа, которая уже работает под вашей учётной записью на этом компьютере, может читать
всё, что можете читать вы, в том числе файлы SMTV, — как и с любой другой программой.

---

## Security (English)

**Reporting a vulnerability.** Report it privately through GitHub: the repository's **Security** tab → **Report a
vulnerability**. Do not open a public issue for it. We answer within a week and credit you in the release notes
unless you prefer not. Only the latest version gets fixes; update from SMTV's window when it offers a new version.

**What SMTV protects.** Keys to AI services stay on your computer (the system's password store or an encrypted file)
and go only to their service; they never appear in the window, logs or problem reports. The SMTV page answers only
on this computer and every request needs a secret only SMTV's own window and page have; the page itself opens only
from SMTV. A phone sees SMTV only after you switch it on and scan a QR code with a fresh secret, and cannot see keys,
update or remove SMTV. Links are downloaded on your computer by yt-dlp when «Download links myself» is on; once the
StreamMoment account opens, a link can also go through its server, which stores nothing. Your own files are sent
nowhere; the stream's text goes only to the AI you chose. Updates come only from a signed list of releases, never an
older one, and only files with matching checksums are installed. Fixes run a program SMTV itself knows, shown before
it runs. Not protected: a program already running under your own account can read what you can, SMTV's files
included.
