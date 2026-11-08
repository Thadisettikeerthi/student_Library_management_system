# 📚 Library Management System (Full-Stack + SQLite)

A modern full-stack web application with persistent SQLite database storage, role-based login portal (Student & Admin), category browsing, live search, borrowing status toggles, and an interactive book insertion modal.

---

## 🚀 How to Run the Project

1. Open your terminal or command prompt inside this folder:
   ```bash
   cd "C:\keerthi\library-management-system"
   ```

2. Start the web application:
   ```bash
   python app.py
   ```
   *(Or simply double-click `run.bat`)*

3. Open your browser and visit:
   👉 **http://localhost:3000**

---

## 🔑 Login Portals & Access Credentials

The login page features two distinct category boxes:

### 1. 🎓 Student Portal
- **Role:** Student
- **Password:** `student`
- **Access:** Browse catalog, view real-time availability counts, borrow & return books, access online digital reading room.

### 2. 🛡️ Admin Portal
- **Role:** Admin
- **Password:** `@books1234`
- **Forgot Password Recovery Key:** `bookslibrary`
- **Access:** Full administrative privileges, insert books directly via modal, delete records, update digital reading links.

---

## 🛠️ Features
- **Direct "+ Add New Book" Access:** Add modal opens directly upon click without interrupting popups.
- **Medium-Level Slate Theme:** Balanced, comfortable modern slate gray design with optimal contrast and readability.
- **Permanent SQLite Storage:** All data (books, reading links, and admin passwords) is saved directly in `library.db` on your hard drive.
- **Curated Categories:**
  - 💼 **Entrepreneurs:** *Shoe Dog*, *Zero to One*, *The Lean Startup*, *Elon Musk*, *Steve Jobs*, *Principles*
  - 🤖 **Technology & AI:** *Clean Code*, *Artificial Intelligence*, *Designing Data-Intensive Applications*, *Clean Architecture*
  - 🧠 **Psychology & Mindset:** *The Psychology of Money*, *Atomic Habits*, *Thinking, Fast and Slow*, *Deep Work*
  - 🏛️ **Philosophical:** *Meditations*, *Beyond Good and Evil*, *The Republic*, *The Myth of Sisyphus*
  - ⚡ **Comics:** *Watchmen*, *Batman: Year One*, *Spider-Man: Blue*, *Maus*
- **Digital Reading Room:** Free access to 20+ full-text online public domain books with direct browser readers.
- **Availability Toggles:** Click **"Borrow Book"** or **"Return Book"** to instantly update status between *Available* and *Checked Out*.
