# Harvard-s-Artifacts-Collection
**🎨 Harvard Art Museum Data Explorer**

This project is a Streamlit-based web application that allows users to explore and analyze data from the Harvard Art Museum API & MySQL database in a clean and interactive way.

**🔑 Key Features**

• Classification-Based Exploration: Select an artifact classification (e.g., Coins, Paintings, Prints) and instantly view related Metadata, Media, and Color data side by side.

• Pretty JSON View: Artifact details are displayed in a readable, color-coded JSON format, making it easy to understand raw data.

• SQL Integration: The app supports data migration into MySQL. Once inserted, artifacts are displayed in a scrollable, full-width SQL table for deeper exploration.

• Tabbed Navigation: The interface provides three intuitive tabs:

• Select Your Choice → Browse data from classifications

• Migrate to SQL → Insert & view collected records in SQL tables

• SQL Queries → Run custom SQL queries with built-in error handling for empty results

• Performance Optimized: Data is fetched and displayed quickly without repetitive API calls.

**⚙️ Tech Stack**

• Frontend: Streamlit

• Backend: Python, MySQL (MariaDB)

• Database Access: mysql-connector-python, SQLAlchemy

• Data Handling: Pandas

**🚀 Use Cases**

• Art researchers & students exploring museum data

• Developers learning API-to-SQL pipelines

• Anyone interested in data visualization and digital humanities
