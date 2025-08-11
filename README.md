

<img width="2048" height="786" alt="Gemini_Generated_Image_qdxpewqdxpewqdxp" src="https://github.com/user-attachments/assets/77af471c-8863-4d02-af12-b1faef0658d1" />




# Tsa-Security - Система за видеонаблюдение

[English Version](#tsa-security---video-surveillance-system)

**Tsa-Security** е модерно и интуитивно десктоп приложение за видеонаблюдение, създадено с **PySide6**. То предоставя на потребителите възможност за наблюдение в реално време, запис и управление на камери. Със своя изчистен и модерен тъмен интерфейс, приложението е подходящо както за стандартни потребители, така и за администратори, които се нуждаят от повече контрол.

## 🌟 Характеристики

* **Управление на потребители**: Приложението поддържа две потребителски роли - **Administrator** и **Standard**. Администраторите имат пълен достъп до всички функционалности.
* **Динамичен интерфейс**: Интерфейсът се адаптира спрямо ролята на потребителя, като скрива администраторските панели от стандартните потребители.
* **Отдалечен достъп чрез Tailscale**: Позволява сигурно наблюдение на камерите от всяка точка на света, без нужда от сложни настройки като "port forwarding". Вашият офисен компютър се превръща в персонален NVR.
* **Наблюдение в реално време**: Показва видео потоци от множество камери в конфигурируема мрежа (1x1, 2x2, 3x3), с възможност за избор на конкретна камера.
* **Управление на камери**: Позволява лесно добавяне, редактиране и изтриване на камери, както и сканиране на локалната мрежа за автоматично откриване.
* **Запис и снимки**: Предлага ръчен запис и правене на снимки от видео потока с един клик.
* **Детекция на движение**: Системата може да засича движение в кадър и да индикира това визуално с червена рамка.
* **Преглед на събития**: Специализиран раздел за преглед на записи и събития, с възможност за филтриране по камера и тип на събитието.
* **Персонализация**: Настройки за промяна на темата, изгледа по подразбиране и пътя за съхранение на записите.
* **Модерен дизайн**: Използва **QSS** за стилизиране, което осигурява професионален и консистентен изглед.

## 🚀 Първи стъпки

1.  **Клонирайте хранилището**:
    ```bash
    git clone [https://github.com/your-username/tsa-security-redesign1.git](https://github.com/your-username/tsa-security-redesign1.git)
    ```
2.  **Инсталирайте зависимостите**:
    ```bash
    pip install PySide6 opencv-python onvif-zeep
    ```
3.  **Стартирайте приложението**:
    ```bash
    python main.py
    ```

## 💻 Употреба

При стартиране ще бъдете посрещнати от екран за вход. Можете да използвате следните данни от `data/users.json`:

* **Администратор**:
    * **Потребителско име**: `admin`
    * **Парола**: `password`
* **Стандартен потребител**:
    * **Потребителско име**: `user`
    * **Парола**: `user`

## 🔒 Настройка за отдалечен достъп (Tailscale)

Тази функционалност превръща компютъра, на който е инсталирана програмата (напр. в офиса), във ваш личен NVR сървър, достъпен отвсякъде.

### Стъпка 1: На компютъра-сървър (в офиса)

1.  **Инсталирайте Tailscale** от официалния сайт и влезте в акаунта си.
2.  **Споделете локалната мрежа**. Отворете Command Prompt **като Администратор** и изпълнете командата. Заменете `192.168.1.0/24` с обхвата на вашата мрежа, ако е различен.
    ```bash
    tailscale up --advertise-routes=192.168.1.0/24
    ```
3.  **Одобрете мрежата** от админ конзолата на Tailscale.

### Стъпка 2: На отдалеченото устройство (напр. лаптоп вкъщи)

1.  **Инсталирайте Tailscale** и влезте със **същия акаунт**.
2.  **Инсталирайте TSA-Security** (копирайте папката с програмата и инсталирайте зависимостите).

### Стъпка 3: Свързване

Стартирайте TSA-Security на отдалеченото устройство. Добавете камерите, като използвате техните **оригинални, локални IP адреси** (напр. `rtsp://192.168.1.14:554/`). Tailscale ще се погрижи за останалото.

## 🛠️ Технологии

* **Python 3**
* **PySide6**: За изграждане на графичния потребителски интерфейс.
* **OpenCV**: За обработка на видео потоци.
* **QSS (Qt Style Sheets)**: За стилизиране на интерфейса.

---

# Tsa-Security - Video Surveillance System

[Българска версия](#tsa-security---система-за-видеонаблюдение)

**Tsa-Security** is a modern and intuitive desktop application for video surveillance, created with **PySide6**. It provides users with the ability to monitor in real-time, record, and manage cameras. With its clean and modern dark interface, the application is suitable for both standard users and administrators who need more control.

## 🌟 Features

* **User Management**: The application supports two user roles - **Administrator** and **Standard**. Administrators have full access to all functionalities.
* **Dynamic Interface**: The user interface adapts to the user's role, hiding administrative panels from standard users.
* **Remote Access via Tailscale**: Allows secure monitoring of your cameras from anywhere in the world, without the need for complex configurations like port forwarding. Your office PC becomes a personal NVR.
* **Real-time Monitoring**: Displays video streams from multiple cameras in a configurable grid (1x1, 2x2, 3x3), with the ability to select a specific camera.
* **Camera Management**: Allows for easy adding, editing, and deleting of cameras, as well as scanning the local network for automatic discovery.
* **Recording and Snapshots**: Offers one-click manual recording and snapshots from the video stream.
* **Motion Detection**: The system can detect motion in the frame and visually indicate it with a red border.
* **Event Review**: A dedicated section for reviewing recordings and events, with options to filter by camera and event type.
* **Customization**: Settings to change the theme, default grid view, and the storage path for recordings.
* **Modern Design**: Uses **QSS** for styling, providing a professional and consistent look.

## 🚀 Getting Started

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/tsa-security-redesign1.git](https://github.com/your-username/tsa-security-redesign1.git)
    ```
2.  **Install the dependencies**:
    ```bash
    pip install PySide6 opencv-python onvif-zeep
    ```
3.  **Run the application**:
    ```bash
    python main.py
    ```

## 💻 Usage

Upon launching, you will be greeted by a login screen. You can use the following default credentials from the `data/users.json` file:

* **Administrator**:
    * **Username**: `admin`
    * **Password**: `password`
* **Standard User**:
    * **Username**: `user`
    * **Password**: `user`

## 🔒 Setting up Remote Access (Tailscale)

This functionality turns the computer running the application (e.g., in your office) into your personal NVR server, accessible from anywhere.

### Step 1: On the Server PC (in the office)

1.  **Install Tailscale** from the official website and log into your account.
2.  **Share the local network**. Open Command Prompt **as an Administrator** and run the command. Replace `192.168.1.0/24` with your network's range if it's different.
    ```bash
    tailscale up --advertise-routes=192.168.1.0/24
    ```
3.  **Approve the routes** from your Tailscale admin console.

### Step 2: On the Remote Device (e.g., your laptop at home)

1.  **Install Tailscale** and log in with the **same account**.
2.  **Install TSA-Security** (copy the program folder and install the dependencies).

### Step 3: Connect

Run TSA-Security on your remote device. Add your cameras using their **original, local IP addresses** (e.g., `rtsp://192.168.1.14:554/`). Tailscale will handle the rest.

## 🛠️ Technologies

* **Python 3**
* **PySide6**: For building the graphical user interface.
* **OpenCV**: For processing video streams.
* **QSS (Qt Style Sheets)**: For styling the interface.
