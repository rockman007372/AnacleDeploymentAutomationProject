# README

## Overview

This repository contains automation scripts used at my workplace, **Anacle (MRI Software)**, to streamline repetitive development tasks.

---

## `update_schema.py`

A Python script that automates the process of fetching and executing database schema update scripts.

### Problem

Previously, after rebuilding the **LogicLayer** project (which defines backend models), developers had to:

1. Click a button on the web app (after IIS reload delays) to download a schema update SQL script.
2. Open the script in SSMS and run it manually.
3. Wait for the script to update **every** table in the database—even unchanged ones—making the process mind-bogglingly slow.

### Solution

`update_schema.py` automates this entire process:

* **Fetches** the SQL schema update script directly from the web app.
* **Filters** it to include only tables specified in the config file.
* **Executes** the filtered script on SQL Server automatically.

It solves both problems of manual fetching of SQL script and slow script execution time.

---

### Configuration

Example `config.json`:

```json
{
  "log_dir": "./logs/",
  "url": "http://localhost/SP/applogin.aspx",
  "update_all_tables": false,
  "tables": ["GiroDeduction", "GiroAdhocDeduction"],
  "validate_script_before_execution": true,
  "databases": ["abell.v10.0-MyBill-Deve", "abell.v10.0-MyBill-SP"]
}
```

#### Config Options

| Key                                  | Description                                                                                                        |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| **log_dir**                          | Directory where execution logs will be stored.                                                                     |
| **url**                              | The web app URL used to fetch the schema update script.                                                            |
| **update_all_tables**                | If `true`, runs the full script on all tables. If `false`, limits updates to specified tables.                     |
| **tables**                           | List of table names to include when filtering the SQL script. Ignored if `update_all_tables` is `true`.            |
| **validate_script_before_execution** | If `true`, spawns a new console to preview the script and ask for permission to proceed execution.                 |
| **databases**                        | List of databases to execute the schema update script on. **If empty, use the database in the connection string**. |


### Setup and Run

1. Create a `.env` file in `./configs/` directory and add your database connection information.

```env
server=servername
database=dbname
uid=username 
pwd=pasword
```

2. Update the `update_schema_config.json` file in `./configs/` directory.

3. Run from the project root (where this README is located):

```cmd
python scripts/update_schema.py
```

### Notable implementations
- If multiple databases are specified, `update_schema.py` can execute the SQL script on these databases in parallel using `concurrency.futures.ThreadPoolExecutor` library.
- The whole SQL deployment pipeline are abstracted into `utils/pipeline.py`. This allows the pipeline to be reused as a package in other scripts.

## `build.py`

A simple console app that builds specific projects in `abell.sln`.

Previously, developers at Anacle are adviced to build the projects in the IDE (Visual Studio, Rider), which made it hard to automate the build process in a script. After some research and experimentation, I discovered how to build them from the command line.

### How to build using command line

To build any projects, we must first open the Visual Studio Development Command (`VsDevCmd.bat`). The `VsDebCmd` instantiates environment variables and macros that allow post-build events to be executed for certain projects (e.g. `LogicLayer.csproj`).

```cmd
"C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/Tools/VsDevCmd.bat"
```

Once `VsDebCmd` is run, you can build any projects using the `msbuild` command. For example, to build `LogicLayer.csproj`:

```cmd
msbuild "PATH_TO_SOLUTION" /t:LogicLayer:Rebuild /v:diag
```
> [!WARNING]
> You must build the project by calling `msbuild` on the solution path (e.g. `.../abell.root/abell/abell.sln`), then specifies the project name in the `/t` flag. This ensures post-build events are executed.

Some projects require us to publish instead of just building. To publish a project, run:

```cmd
msbuild "PATH_TO_PROJECT" /p:DeployOnBuild=true /p:PublishProfile=DevOpsDebug /p:Configuration=Debug /v:m
```