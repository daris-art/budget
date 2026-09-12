# Budget Application

A professional budget management application built with PyQt6. This application helps you track expenses, manage budgets, and generate financial reports with Bitcoin price integration.

## Features

- **Expense Management**: Add, edit, and delete expenses with categories, dates, and amounts
- **Category Organization**: Organize expenses by custom categories
- **Data Validation**: Built-in validation for all data entries
- **Database Management**: SQLite database for persistent data storage
- **Import/Export**: Import and export financial data to/from various formats
- **Bitcoin Integration**: Real-time Bitcoin API integration for cryptocurrency tracking
- **Graph Visualization**: Visual representation of expense data
- **PDF Reports**: Generate professional PDF reports of your budget
- **Dark Theme**: Professional dark theme UI with PyQt Dark Theme
- **Task Workers**: Asynchronous task processing for smooth user experience

## Project Structure

```
budget/
├── main.py                      # Application entry point
├── controller.py                # Business logic controller (MVC pattern)
├── view.py                      # Main UI view (MVC pattern)
├── graph_view.py                # Graph visualization component
├── migrate_json_to_sqlite.py   # Data migration utility
├── bob.sh                       # Shell script utility
├── requirements.txt             # Project dependencies
│
├── core/                        # Core application modules
│   ├── __init__.py
│   ├── model.py                # Data model (MVC pattern)
│   ├── data_models.py          # Data classes and exceptions
│   ├── database.py             # Database management and queries
│   ├── services.py             # Business services (import/export, API)
│   └── validation.py           # Data validation logic
│
├── ui/                          # UI components
│   ├── __init__.py
│   └── custom_widgets.py       # Custom PyQt6 widgets
│
├── workers/                     # Async task workers
│   ├── __init__.py
│   └── task_workers.py         # Background task processing
│
└── tests/                       # Test suite
    ├── test_bitcoin_service.py
    ├── test_database.py
    ├── test_model_filtering.py
    └── test_pdf_report.py
```

## Architecture

This application follows the **Model-View-Controller (MVC)** pattern:

- **Model** (`core/model.py`): Manages application data and business logic
- **View** (`view.py`): Handles the user interface with PyQt6
- **Controller** (`controller.py`): Mediates between Model and View

### Core Components

- **DatabaseManager**: Handles all SQLite database operations
- **DataValidator**: Validates user input and data integrity
- **ImportExportService**: Manages data import/export operations
- **BitcoinAPIService**: Integrates with Bitcoin API for real-time data

## Installation

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Setup

1. Clone or download this project:
```bash
cd budget
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies

- **PyQt6**: GUI framework
- **matplotlib**: Data visualization and graphing
- **requests**: HTTP library for API calls
- **openpyxl**: Excel file handling
- **pyqtdarktheme**: Dark theme for PyQt6
- **reportlab**: PDF generation

## Usage

### Running the Application

```bash
python main.py
```

### Data Migration

To migrate data from JSON to SQLite:

```bash
python migrate_json_to_sqlite.py
```

## Testing

Run the test suite:

```bash
pytest tests/
```

Individual test modules:
- `test_bitcoin_service.py`: Bitcoin API integration tests
- `test_database.py`: Database operations tests
- `test_model_filtering.py`: Data filtering tests
- `test_pdf_report.py`: PDF report generation tests

## Development

### Key Features to Explore

1. **Expense Management**: Track expenses with dates, amounts, and categories
2. **Budget Analytics**: View spending patterns through graphs
3. **Report Generation**: Create PDF reports of budget summaries
4. **Data Import/Export**: Transfer data to other formats
5. **Bitcoin Tracking**: Monitor Bitcoin prices alongside expense data

### Project Conventions

- All database operations go through `DatabaseManager`
- All user input is validated through `DataValidator`
- Business logic is handled in `core/services.py`
- UI components are in `view.py` and `ui/custom_widgets.py`
- Asynchronous tasks use `task_workers.py`

## Configuration

Configuration files are typically stored in `~/.config/` or project directories. Database files are stored locally for easy access and backup.

## Troubleshooting

### Common Issues

- **Import Errors**: Ensure all dependencies are installed via `pip install -r requirements.txt`
- **Database Errors**: Check that you have write permissions in the project directory
- **API Errors**: Verify internet connection for Bitcoin API calls

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions, please refer to the test files for usage examples of each component.

---

**Last Updated**: 2026-09-12
