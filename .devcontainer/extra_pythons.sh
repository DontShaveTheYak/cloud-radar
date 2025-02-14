#!/bin/bash

pyenv install -s 3.9.20
pyenv install -s 3.10.15
pyenv install -s 3.11.10
pyenv install -s 3.13.0
pyenv global 3.12.7 3.13.0 3.11.10 3.10.15 3.9.20
pyenv rehash
