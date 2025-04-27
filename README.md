# Smart Attendance Tracker

A simple and efficient attendance tracking system built with Python Flask, SQLite, and QR code scanning capabilities.

## Features

- 🔐 Role-based authentication (Admin/Lecturer)
- 📱 QR code scanning for quick attendance
- ⌨️ Manual ID entry option
- 📊 Attendance reports and analytics
- 📄 Export attendance data to CSV
- 📝 Manual attendance corrections
- 📈 Visual attendance trends

## Tech Stack

- Frontend: HTML5, CSS3, Vanilla JavaScript
- Backend: Python (Flask Framework)
- Database: SQLite
- QR Code Generation: Python qrcode library
- QR/ID Scanning: HTML5 QR Scanner

## Project Structure

```
/attendance-tracker
├── /static
│    ├── /css
│    ├── /js
│    └── /images
├── /templates
│    ├── login.html
│    ├── dashboard.html
│    ├── scan.html
│    ├── manual_attendance.html
│    └── reports.html
├── app.py
├── models.py
├── init_db.py
└── README.md
```

## Setup Instructions

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install flask flask-login flask-sqlalchemy qrcode opencv-python pandas
```

3. Initialize the database with test data:
```bash
python init_db.py
```

4. Run the application:
```bash
python app.py
```

5. Access the application at `http://localhost:5000`

## Test Credentials

- Admin:
  - Email: admin@example.com
  - Password: admin123

- Lecturers:
  - Email: john.smith@example.com
  - Password: lecturer123
  - Email: sarah.johnson@example.com
  - Password: lecturer123

## Usage Flow

1. Login as Admin or Lecturer
2. View dashboard with courses and attendance options
3. Take attendance via:
   - QR code scanning
   - Manual ID entry
4. View attendance reports
5. Export attendance data to CSV

## License

MIT License