UMB Observatory
=================

This project manages a joint docker file with selected versions of different PMC tools and libraries,
a jupyter server, and a collection of python files that help to ensure that are mutually compatible. 


The container
-------------
Is created from the docker file, released to github daily via CI. 
On the container, you find 
- a version of storm (with UMB support),
- a version of prism (with UMB support),
- the umbi python library.
- the contents of this repo, in particular, the umbtest library.
- A jupyter notebook that is running. 

### Running the docker

You can build the docker container yourself or obtain it by:

```
docker pull ghcr.io/pmc-tools/umb-observatory:main
```

Then, to start it, we recommend:
```
docker run --name pmcdocker -d -p 8000:8000 ghcr.io/pmc-tools/umb-observatory:main
```

The exposed port helps you connect to the notebooks. If port 8000 is already occupied locally,
you can change it to `-p 8001:8000`, or something like that. 

### Connecting to the notebook

First, run 
```
docker exec pmcdocker jupyter server list
```
The link in there will typically not work. However, you can find a token as part of the listed url. 
Copy this token. 

You can connect to `localhost:8000` (or another port, if you changed it) in your browser.
The notebook will ask for a token. Paste the token you just copied. 
You are now in a jupyter notebook. 

You can go to getting_started.ipynb to get started with some opportunities that UMB offers.


Umbtest
-------

Umbtest is a set python files that check that UMB support is aligned. 
The best place to get started is probably in `tests/test_toolchains.py`.
Roughly `umbtest/benchmarks.py` collects files we use for testing,
while `umbtest/tools.py` provides a thin layer around the available tools. 

You can use umbtest in different ways. 
The preferred way is via the docker, which ensures that you have the right tools installed in known locations. 

### Via the docker
This is possible in two ways: via a notebook and via the command line. 

#### Via the notebook
As explained in the notebook, to which you can connect as explained above. 

#### From the command line
In particular, you can run: 
```
docker exec pmcdocker python -m pytest 
```

### Locally
UMBTest is currently not available as a standalone package.
However, you can run the scrips directly on your local machine.

1. Update the `tools.toml` file with your local location of the tools.
2. `pip install umbi`
3. - You can run `python -m pytest tests` to run all kind of tests
   - Run `python main.py` for a simple script
   - Or run the python notebook on your local jupyterserver (see above for details)

Continuous Integration
-----------------------
This repo is hosted on github, where continuous integration runs Umbtests:
https://github.com/pmc-tools/umb-observatory/actions/workflows/test.yml

