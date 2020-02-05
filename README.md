# CrConnectFrontend

[![Build Status](https://travis-ci.com/sartography/cr-connect-workflow.svg?branch=master)](https://travis-ci.com/sartography/cr-connect-workflow)

# CR Connect Workflow Microservice
## Development Setup
### Tools
These instructions assume you're using these development and tools:
- IDE: PyCharm Professional Edition
- Operating System: Ubuntu

### Environment Setup
Make sure all of the following are properly installed on your system:
1. `python3` & `pip3`:
    - [Install python3 & pip3](https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-18-04-server)
    - [Installing Python 3 on Linux](https://docs.python-guide.org/starting/install3/linux/)
2. `pipenv`:
    - [Install pipenv](https://pipenv-es.readthedocs.io/es/stable/)
    - [Add ${HOME}/.local/bin to your PATH](https://github.com/pypa/pipenv/issues/2122#issue-319600584)

### Project Initialization
1. Clone this repository.
2. In PyCharm:
    - Go to `File > New Project...`
    - Click `Pure Python` (NOT `Flask`!!)
    - Click the folder icon in the `Location` field.
    - Select the directory where you cloned this repository and click `Ok`.
    - Expand the `Project Interpreter` section.
    - Select the `New environment using` radio button and choose `Pipenv` in the dropdown.
    - Under `Base interpreter`, select `Python 3.6`
    - In the `Pipenv executable` field, enter `/home/your_username_goes_here/.local/bin/pipenv` 
    - Click `Create`
        ![Project Interpreter](readme_images/new_project.png)
3. PyCharm should automatically install the necessary packages via `pipenv`. 
For me, the project interpreter did not set set up for me correctly on first attempt.  I had to go
to File -> Settings -> Project Interpreter and again set the project to use the correct PipEnv 
environment. Be sure that your settings like simliar to this, or attempt to add the interpreter again
by clicking on the gear icon.
![Project Interpreter Settings screen](readme_images/settings.png) 

4. With this properly setup for the project, you can now right click on the run.py and set up a new 
run configuration and set up a run configuration that looks like the following (be sure to save this 
run configuration so it doesn't go away.) :
![Run Configuration Screenshot](readme_images/run_config.png)

### Running the Web API
Just click the "Play" button next to RUN in the top right corner of the screen.
The Swagger based view of the API will be avialable at http://0.0.0.0:5000/v1.0/ui/

### Testing from the Shell
This app includes a command line interface that will read in BPMN files and let you 
play with it at the command line.  To run it right click on app/command_line/joke.py and
click run.  Type "?" to get a list of commands. 
So far the joke system will work a little, when you file it up try these commands
in this order:
```bash
> engine  (this will run all tasks up to first user task and should print a joke)
> answer clock (this is the correct answer)
> next (this completes the user task)
> engine (this runs the rest of the tasks, and should tell you that  you got the question right)
```

You can try re-running this and getting the question wrong.
You might open up the Joke bpmn diagram so you can see what this looks like to 
draw out.

## Documentation
Additional Documentation is available on [ReadTheDocs](https://cr-connect-workflow.readthedocs.io/en/latest/#)

### Additional Reading

1. [BPMN](https://www.process.st/bpmn-tutorial/)  Is the tool we are using to create diagrams
of our business processes.  It's is a beautiful concise diagramming tool. We strongly recommend you 
read this complete tutorial, as this notation is the foundation on which this project as well as many
other software systems for businesses are built.  Know it well.

### Notes on Creating Good BPMN Diagrams in Comunda
1. Be sure to give each task a thoughtful (but unique!) id. This will 
make the command line and debugging far far easier.  I've tended to pre-fix
these, so task_ask_riddle if a task is asking a riddle for instance.
