curr_loc=$(pwd)
cd ./Python/ || cd ../Python/ || exit 1;
uv run --active --frozen alembic "$@";
cd "$curr_loc" || exit 1;
