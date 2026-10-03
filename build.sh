#!/bin/sh
set -eu
ocamlc -c worker_api.ml
ocamlc -I +compiler-libs -c compiler_worker.ml
ocamlc -a -linkall -I +compiler-libs ocamlcommon.cma ocamlbytecomp.cma compiler_worker.cmo -o compiler_worker.cma
ocamlc -linkall -I +unix -I +dynlink unix.cma dynlink.cma worker_api.cmo lemon.ml -o lemon.byte
