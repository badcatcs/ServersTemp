# ServersTemp by ProConnectX [xxx]

Мониторинг температур серверов Linux/Proxmox с красивым веб-интерфейсом.

## Возможности
- Сбор и хранение температур с CPU, GPU, NVMe, материнской платы и других сенсоров
- Автоматическая категоризация сенсоров (ядра, пакет, GPU, плата и др.)
- График температур по серверам за неделю
- Цветовая индикация температур и статусов
- Фильтрация по серверу
- Переключение светлой/тёмной темы и языка (RU/EN)
- Автоматическая очистка старых логов (старше 7 дней)
- Полностью автономная работа (без интернета)

## Установка
1. Установите на серверах файл servers-temp.sh через wget:
   ```bash
   wget https://raw.githubusercontent.com/badcatcs/ServersTemp/refs/heads/main/servers-temp.sh
   ```
   Установка через curl:
   ```bash
   curl -L -o servers-temp.sh https://raw.githubusercontent.com/badcatcs/ServersTemp/refs/heads/main/servers-temp.sh
   ```
2. Выдача прав для servers-temp.sh:
   ```bash
   sudo chmod +x servers-temp.sh # Права доступа
   ```
3. Установка servers-temp.sh:
   ```bash
   sudo ./servers-temp.sh -h server_*НазваниеСервера* -ip *IPГлавногоСервера* -t -a -i
   ```
4. Установите остальные файлы на виртуальную машину/главный сервер:
   ```bash
   git clone https://github.com/badcatcs/ServersTemp.git
   cd ServersTemp
   python3 -m pip install -r requirements.txt
   ```

### Опции для запуска servers-temp.sh:
    -h  <--- Название сервера, которое будет отображаться на сайте. Пример: -h server_my-server1 (По умолчанию: server_main)
    -ip <--- IP адрес главного сервера. Пример -ip 192.168.0.111
    -t  <--- TCP протокол - Порт 5142 (По умолчанию: UDP - Порт 5141)
    -i  <--- Установка скрипта в автозапуск
    -a  <--- Автоматическая установка пакетов (lm-sensors)

    ## Примеры:
       sudo ./servers-temp.sh -h server_my-server1 -ip 192.168.0.111 # UDP Протокол - Порт 5141
       sudo ./servers-temp.sh -h server_my-server1 -ip 192.168.0.111 -t # TCP Протокол - Порт 5142
       sudo ./servers-temp.sh -i -a # Автозапуск + Установка пакетов

    ### Рекомендация:
       sudo ./servers-temp.sh -h server_*НазваниеСервера* -ip *IPГлавногоСервера* -t -a -i # TCP Протокол, Автозапуск и Установка пакетов
## Запуск
1. Запустите Flask API на своём главном сервере - backend:
   ```bash
   python3 servers_temp_api.py
   ```
2. Рекомендую настроить правила сети через UFW, указав свои физические сервера, а так же доступ только для вашего ПК
   ```bash

   # Настройка доступа
   sudo ufw allow from *IP Вашего ПК* to any port 22 proto tcp # Доступ для вашего ПК SSH Протокол для консоли
   sudo ufw allow from *IP Вашего ПК* to any port 80 proto tcp # Доступ для вашего ПК Локальный сайт сенсеров

   # Пример TCP Protocol (Наилучший, при указании в servers-temp.sh -t -> [Порт 5142])
   sudo ufw allow from *IP Вашего Сервера1* to any port 5142 proto tcp # Приём сенсоров с ваших серверов на главный
   sudo ufw allow from *IP Вашего Сервера2* to any port 5142 proto tcp # Приём сенсоров с ваших серверов на главный
   sudo ufw allow from *IP Вашего Сервера3* to any port 5142 proto tcp # Приём сенсоров с ваших серверов на главный

   # Пример UDP Protocol (Дополнительный - необязательный -> [Порт 5141])
   sudo ufw allow from *IP Вашего Сервера1* to any port 5141 proto udp # Приём сенсоров с ваших серверов на главный

   sudo ufw enable # Включение правил безопасности
   ```
3. Откройте сайт на другом ПК, указав IP адрес главного сервера, пример: [http://192.168.0.111](http://192.168.0.111)

## Как это работает
- Bash-скрипт на сервере собирает данные с помощью `lm-sensors` и отправляет их на backend
- Backend сохраняет данные в SQLite и отдаёт их на фронтенд
- Веб-интерфейс отображает карточки серверов, график температур и статусы серверов

## Локальный Сайт
![Dark-Theme](https://github.com/user-attachments/assets/253c47f6-1cf8-45fb-94fc-a4a02e11abee)
![White-Theme](https://github.com/user-attachments/assets/a200c050-8f11-4822-a9c4-15a87c6baf45)

## Удаление скрипта на серверах
   ```bash
   wget https://raw.githubusercontent.com/badcatcs/ServersTemp/refs/heads/main/uninstall-servers-temp.sh
   sudo chmod +x uninstall-servers-temp.sh # Права доступа
   sudo ./uninstall-servers-temp.sh # Полное удаление с очисткой
   ```

## Лицензия
MIT
