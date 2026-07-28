curr_loc=$(pwd)
cd ./Python/ || cd ../Python/ || exit 1;
alembic "$@";
cd "$curr_loc" || exit 1;
