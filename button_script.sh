envPrefix=$1

eval "$(command conda shell.bash hook 2> /dev/null)"
conda run -p "${envPrefix}" python "$EXTENSIONS_DIR/toolbar-button/conda_env_export.py" > "$HOME/environment.yaml"