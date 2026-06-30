# Hera Project Tracker

A lightweight, web-based task and project tracking application designed to help teams and individuals manage their workflows efficiently. Built with Python, Flask, and SQLite.

## Features

- **Dynamic Task Prioritization:** Organize tasks by periods like "This Week", "Next Week", or "This Month".
- **Exact Date Mapping:** Assign specific deadlines to tasks; the system automatically calculates the appropriate target period based on the current date (calculating weeks from Friday to Friday).
- **Drag & Drop Sorting:** Manually reorder your open tasks to set custom priorities using an intuitive drag-and-drop interface.
- **Task History Logging:** Keep track of every change made to a task, including status updates, date changes, and completion tracking.
- **Multilingual Support:** Fully functional in both English and Turkish, switchable directly from the UI.
- **Responsive UI:** Clean, modern, and easy-to-use interface with color-coded badges for visual urgency.

## Tech Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite3
- **Frontend:** HTML5, Vanilla CSS, JavaScript, SortableJS

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ederya/hera_project_tracker.git
   cd hera_project_tracker
   ```

2. **Install dependencies:**
   Make sure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Access the app:**
   Open your web browser and go to: `http://localhost:5050`

## Notes
- The database (`hera_workflow.db`) is automatically created upon the first run.
- Migration scripts (like `migrate_dates.py`) are included to help format legacy data when updating to the dynamic date system.

---
*Developed as a customized workflow solution.*
