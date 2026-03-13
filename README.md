# Waseet

backend services and RESTful APIs using Django, serving data to the front-end applications (android application).

## Requirements

- Python 3.9
- Django 5.2.5


### Install Python  using MiniConda

1) Download and Install MiniConda from [here](https://www.anaconda.com/docs/getting-started/miniconda/install)
2) Create a new environment using the following command:
```bash
$ conda create -n waseet python=3.9
```
3) Activate the created environment using the command
```bash
$ conda activate waseet
```

## Installation

### Install the required packages
```bash
$ pip install -r requirements.txt
```
### Setup the environment variables
```bash
$ cp .env.example .env
```
Set your environment variables in the .env file. Like Django Secret Key.