# Machine App Template

## Overview
The purpose of this project is to provide users with a framework upon which they can construct their own Machine Applications. High-level goals include:
- A clean interface to interact with multiple machine motions at a time
- A web-based user interface that is easy to extend
- A mechanism for broadcasting messages to facilitate the real-time updating of the web UI.

## Getting Started
1. Clone the repository to a new directory on your machine
2. Download Python 3.5 (https://www.python.org/downloads/)
3. Run `python --version` or `python3 --version` in the commandline to check that you have installed properly
4. Install server dependencies by running `cd server && pip install -r requirements.txt` (See `requirements.txt` to view the external libraries that the server relies on)
5. Run the server using `cd server && python app.py` (You may need to use `python3` or event `python35` instead of python, depending on how your paths were set up)
6. Start hacking! The project is now all yours to play around with. I recommend reading the [documentation](./docs/getting_started.md) before going any further.


## Development Environment Recommendation
We recommend building your program in Visual Studio Code with the following extensions:
1. Python by Microsoft - Provides debugging support and a seamless way to manage multiple versions of Python
2. Python for VSCode - Provides autocompletion recommendations for Python

With these extensions installed, you will be able to run the server in `Debug` mode by clicking the debug button in Visual Studio's side bar, selecting `Application` from the dropdown, and clicking the playing button. Running in debug mode will allow you to set breakpoints and inspect the state of your application at run time.

## Deploying your MachineApp
After developing yout application locally, you may want to deploy it to your MachineMotion controller. To do this:
1. Connect your computer to your MachineMotion controler
2. Run `python upload.py` from the project's root directory. This script will prompt you for your password three times.
3. Run `restart_server.py` from the project's root directory.
4. Navigate to `192.168.7.2:3011` to see your MachineApp running