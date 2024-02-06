# /bin/bash

python DirectoryService.py --open --port 9000 &

python Client.py --open --dir $1 --verbose &

python Logger.py --open --dir $1 --verbose &
python Solver.py --open --dir $1 --verbose &
python LetterCounter.py --open --dir $1 --verbose &
python Arithmetic.py --open --dir $1 --verbose &

