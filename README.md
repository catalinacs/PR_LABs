# LAB 1 PR: HTTP file server with TCP sockets
In this lab, I implemented a basic HTTP file server in Python that allows directory navigation, including access to nested folders and files.

## Contents of Directory
* The root directory contains several subfolders. The *Downloads* folder is designated for files saved by the client. The *Public* directory includes additional subdirectories, along with various HTML, PNG, and PDF files used for testing. Other nested directories, such as *books* and *docs*, also include similar test files. The *Report* folder stores images utilized in this report.
* The *Dockerfile* defines the setup for both the server and client containers—specifying dependencies and instructions to run the Python applications within Docker. The *docker-compose.yml* file coordinates these containers, launching both services, linking them together, mapping ports, and managing shared storage volumes.
* The *server.py* script processes HTTP requests, locates the requested files within the directory, and sends them back to the client.
* The *client.py* script connects to the server, requests specific files, and either displays or saves the received data into the downloads folder depending on the file type.
 
    ![contents.png](public/report/contents.png)

## Dockerfile
The *Dockerfile* makes sure to set a lightweight Python 3.12 environment, copies the server and client scripts into the container’s /app directory, sets it as the working directory, and exposes port 8000 so server.py/client.py can use it.
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY server.py client.py ./
EXPOSE 8000
```

## Docker compose
This *docker-compose.yml* file defines two services: a server that runs server.py on port 8000 to host files, and a client that runs client.py to connect to the server,while managing their shared volumes and ensuring the server starts before the client.

```dockerfile
services:
  server:
    build: .
    container_name: pr-web-server
    environment:
      PORT: 8000
    ports:
      - "8000:8000"
    volumes:
      - ./:/app:ro
    command: ["python", "server.py", "/app"]
  client:
      build: .
      entrypoint: [ "python", "client.py" ]
      volumes:
        - ./downloads:/app/downloads
      depends_on:
        - server
```

## Running the project

We can run the project locally using the command:
```python
python3 server.py <path_to_directory>
```
The image below demonstrates how the project can be executed locally, using the root directory of the project as a command-line argument.

![run_python.png](public%2Freport%2Frun_python.png)

We can also run it using docker with the following command:
```
docker compose up server
```

## Content of served directory
If we serve the root we will see the following files and directories in the browser. We can see all types of files, but can access only png, html, pdf files.
![root_dir.png](public/report/root_dir.png)

We can also choose to serve another directory, like *public* (as seen in the following picture). We can do this locally by running a command similar to this: ```python3 server.py public```, or with docker by changing the command line in *docker-compose.yml*.

![public_dir.png](public%2Freport%2Fpublic_dir.png)

## Requesting files
* We can request a **png** file in the browser by accessing its path or by navigating to it through the folders in the listings.

  ![png_request.png](public%2Freport%2Fpng_request.png)

* To request a **pdf** file we do the same as for the png file.
  ![vicious_pdf.png](public%2Freport_pics%2Fvicious_pdf.png)

* We can also request a  **html** and we will see the html page in the browser.
  ![html_request.png](public%2Freport%2Fhtml_request.png)

* If we request an inexistent file or a file with an extension  that is not permitted, we will get the 404 page. We can also click on the *homepage* button to go back to the root directory list.
  ![404.png](public%2Freport%2F404.png)

## Client
We can run the client both locally:
```python
 python3 client.py 0.0.0.0 8000 1_Vicious.pdf
```
or using docker:
```
docker compose run --rm client server 8000 1_Vicious.pdf
```
And we will get the file saved in the *downloads* folder.

![download.png](public%2Freport%2Fdownload.png)

## Browse a friend's server
For this part, I used my friend Condrea Loredana’s server. First we connected to the same hotspot, then she started her server and then she ran ```ifconfig``` on her laptop and gave it to me. After that, I entered in my browser: ```172.20.10.10:8000``` (her ip addres : port) an got the following result: