FROM python:3.6-stretch

ENV PATH=/root/.local/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin

# install node and yarn
RUN apt-get update
RUN apt-get -y install postgresql-client

# config project dir
RUN mkdir /crc-workflow
WORKDIR /crc-workflow

# install python requirements
RUN pip install pipenv
ADD Pipfile /crc-workflow/
ADD Pipfile.lock /crc-workflow/
RUN pipenv install

# include rejoiner code (gets overriden by local changes)
COPY . /crc-workflow/

# run webserver by default
CMD ["pipenv", "run", "python", "/crc-workflow/run.py"]

# expose ports
EXPOSE 5000
