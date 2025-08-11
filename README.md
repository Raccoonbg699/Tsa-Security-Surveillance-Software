# Tsa-Security - Система за видеонаблюдение

[English Version](#tsa-security---video-surveillance-system)

**Tsa-Security** е модерно и интуитивно десктоп приложение за видеонаблюдение, създадено с **PySide6**. То предоставя на потребителите възможност за наблюдение в реално време, запис и управление на камери. Със своя изчистен и модерен тъмен интерфейс, приложението е подходящо както за стандартни потребители, така и за администратори, които се нуждаят от повече контрол.

## 🌟 Характеристики

* **Управление на потребители**: Приложението поддържа две потребителски роли - **Administrator** и **Standard**. Администраторите имат пълен достъп до всички функционалности, включително управлението на потребители.
* **Динамичен интерфейс**: Потребителският интерфейс се адаптира спрямо ролята на потребителя, като скрива администраторските панели от стандартните потребители.
* **Наблюдение в реално време**: Показва видео потоци от множество камери в конфигурируема мрежа (1x1, 2x2, 3x3).
* **Управление на камери**: Позволява добавяне, редактиране и изтриване на камери.
* **Запис и снимки**: Предлага ръчен запис и правене на снимки от видео потока.
* **Детекция на движение**: Системата може да засича движение в кадър и да индикира това визуално.
* **Преглед на събития**: Специализиран раздел за преглед на записи и събития, с възможност за филтриране по камера и тип на събитието.
* **Персонализация**: Настройки за промяна на темата (тъмна/светла), изгледа по подразбиране и пътя за съхранение на записите.
* **Модерен дизайн**: Използва **QSS** за стилизиране, което осигурява професионален и консистентен изглед на цялото приложение.

## 🚀 Първи стъпки

1.  **Клонирайте хранилището**:
    ```bash
    git clone [https://github.com/your-username/tsa-security-redesign1.git](https://github.com/your-username/tsa-security-redesign1.git)
    ```
2.  **Инсталирайте зависимостите**:
    ```bash
    pip install PySide6 opencv-python
    ```
3.  **Стартирайте приложението**:
    ```bash
    python main.py
    ```

## 💻 Употреба

При стартиране на приложението ще бъдете посрещнати от екран за вход. Можете да използвате следните данни по подразбиране от файла `users.json`:

* **Администратор**:
    * **Потребителско име**: `admin`
    * **Парола**: `password`
* **Стандартен потребител**:
    * **Потребителско име**: `user`
    * **Парола**: `user`

След успешен вход ще бъдете пренасочени към главния екран, откъдето можете да навигирате между различните секции на приложението.

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

* **User Management**: The application supports two user roles - **Administrator** and **Standard**. Administrators have full access to all functionalities, including user management.
* **Dynamic Interface**: The user interface adapts to the user's role, hiding administrative panels from standard users.
* **Real-time Monitoring**: Displays video streams from multiple cameras in a configurable grid (1x1, 2x2, 3x3).
* **Camera Management**: Allows adding, editing, and deleting cameras.
* **Recording and Snapshots**: Offers manual recording and taking snapshots from the video stream.
* **Motion Detection**: The system can detect motion in the frame and indicate it visually.
* **Event Review**: A dedicated section for reviewing recordings and events, with the ability to filter by camera and event type.
* **Customization**: Settings to change the theme (dark/light), default view, and the path for storing recordings.
* **Modern Design**: Uses **QSS** for styling, which provides a professional and consistent look throughout the application.

## 🚀 Getting Started

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/your-username/tsa-security-redesign1.git](https://github.com/your-username/tsa-security-redesign1.git)
    ```
2.  **Install the dependencies**:
    ```bash
    pip install PySide6 opencv-python
    ```
3.  **Run the application**:
    ```bash
    python main.py
    ```

## 💻 Usage

Upon launching the application, you will be greeted by a login screen. You can use the following default credentials from the `users.json` file:

* **Administrator**:
    * **Username**: `admin`
    * **Password**: `password`
* **Standard User**:
    * **Username**: `user`
    * **Password**: `user`

After a successful login, you will be redirected to the main screen, from where you can navigate between the different sections of the application.

## 🛠️ Technologies

* **Python 3**
* **PySide6**: For building the graphical user interface.
* **OpenCV**: For processing video streams.
* **QSS (Qt Style Sheets)**: For styling the interface.