curr_loc=$(pwd)
cd ./Python/ || cd ../Python/ || exit 1;
uv run --frozen --package backend-admin alembic "$@";
cd "$curr_loc" || exit 1;
