
if [ -z "$LD_LIBRARY_PATH" ]
then
   LD_LIBRARY_PATH=""
fi

if [ -z "$PYTHONPATH" ]
then
   PYTHONPATH=""
fi

# Package directories
export ROGUE_DIR=$(dirname -- "$(readlink -f ${BASH_SOURCE[0]})")

# Setup python path
export PYTHONPATH=${ROGUE_DIR}/python:${ROGUE_DIR}/build:${PYTHONPATH}

# Setup library path
export LD_LIBRARY_PATH=${ROGUE_DIR}/build:${LD_LIBRARY_PATH}

