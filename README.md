# GPW Scraping Tool

# What is GPW Scraping Tool?

### GPW (stock exchange) Scraping Tool is a tool that allows you to download reports from the WSE stock exchange. The tool uses a scraping script that automatically downloads reports for selected companies, based on certain parameters.

![](images/app.png)

## Functionality

#### 1. Downloading reports for selected companies from the Stock Exchange.

#### 2. Filtering of reports based on date, report type and category.

#### 3. Ability to download attachments in PDF or HTML format.

#### 4. Exporting data to CSV file.

#### 5. Exporting data to MYSQL database.

#### 6. Summary downloaded reports

#### 7. Displays history searches

## Dictionary

#### `Company name` - Text field where you can post the company name to search.

#### `Report amount` - How many reports would you like to take.

#### `Download the CSV report` - If the box is checked then the CSV file is downloading.

#### `Download` - You can choose witch file type you want download (PDF OR HTML).

#### `Date` - From witch day would you like to check reports.

#### `current` - Actual reports.

#### `semi-annual` - Half-year reports.

#### `quarterfly` - Quarterly reports.

#### `interim` - Interim reports.

#### `annual` - Annual reports.

#### `EBI` - EBI is a system for information dissemination by NewConnect-listed companies.

#### `ESPI` - ESPI is used for mandatory reporting by issuers on the main GPW market.

#### `Run` - This button attempts scraping GPW, download CSV report with scraped data and summary the reports.

## Content

- [user_interface.py](user_interface.py): Gradio-based graphical user interface for convenient parameter entry and display of results.
- [scrape_script.py](scrape_script.py): Script responsible for downloading reports and attachments from the stock exchange.
- [summary.py](summary.py): Part responsible for summarise using local model
- [database_connection.py](database_connection.py): Part responsible for database operations
- [gpw_data.sql](gpw_data.sql): MySQL database with structure and example data
- [REPORTS](REPORTS): folder that will be created when you run the script. Reports and CSV data are saved to it.

## Requirements

- at least 10GB free on disk
- git
- Windows only (for now)
- Internet connection
- NVIDIA GPU (The better the GPU, the faster the summaries will show up )
- `Python 3.12` (Microsoft store)
- any database hosting like XAMPP (https://www.apachefriends.org/pl/download.html)
- ollama installed with `llama3.2:latest` model (https://ollama.com/)

# Installation

Open CMD in desire directory and clone project using:

### Step 1 (clone repository)

```bash
https://github.com/xHezuSx/pracownia-dyplomowa
```

![clone.gif](images/clone.gif)

### Step 2 (setup database)

1. run XAMPP with apache and MYSQL
2. click `Admin` button browser with admin panel will appear
3. select `New` and name database `gpw data` and click `Create`. **IMPORTANT it has to be `gpw data` otherwise it won't work**
4. select `Import` section and select `gpw_data.sql` file from cloned repository
5. scroll down and click `Import`

![import_database.gif](images/import_database.gif)

### Step 3 (setup ollama)

1. Download ollama (https://ollama.com/)
2. Ollama PATH = `C:\Users\<USERNAME>\AppData\Local\Programs\Ollama` <USERNAME> it's your username on Windows
3. open settings search for `environment variables for system`
4. click `environment variables` select `PATH` and `edit`
5. click `New` and paste your ollama PATH

![PATH.gif](images/PATH.gif)

### Step 4 (download model)

1. Open CMD and run download AI model (2GB)

```bash
ollama pull llama3.2
```

2. after download use:

```bash
ollama serve
```

![ollama_pull.gif](images/ollama_pull.gif)

### Step 5 (install dependencies)

On windows right click on folder where project is, select "open in terminal/CMD" option and run following command:

```bash
pip install -r requirements.txt
```

![](images/requirements.gif)

# Information about what has been implemented from the project.

#### In the project, the main idea was to facilitate the work of business analysts by using the AI model to summarize reports from the GPW. In our project it is possible to choose from which period one wants to get the report, in which format to download them (PDF, HTML), in addition to specify the number of reports one wants to get from the official GPW website.

# Information on changes in implementation from the design assumptions with an explanation of why.

#### An additional option that was added during development is the history of recent searches. In doing so, we added a database where search histories are stored.

# Compliance with the project(including the described deviations).

The project was created in accordance with the initial design of the project and there were no deviations from previous documentation.

# Usage

### Step 1 (make sure ollama is running)

- open CMD and use comamnd

```bash
ollama serve
```

### Step 2 (make sure XAMPP (or other MySQL engine) is running)

On windows right click on folder where project is, select "open in terminal/CMD" option and run following command:

### Step 3 (Run app)

If you run app for the first time it will take more time

```bash
python .\user_interface.py
```

if everything is good you should see `Running on local URL:  http://127.0.0.1:7860`. Simply open the link and voilà :)

![](images/run.gif)

Pssst... don't worry about warnings in CMD

# Database

Picture of a relational database

![](images/schemant%20bazy%20danych.png)
