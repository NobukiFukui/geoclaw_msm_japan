#!/bin/bash
make && make data && (make output |tee calc.log)
./sendlocal.sh
