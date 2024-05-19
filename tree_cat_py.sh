#!/bin/bash

# Diretório base
base_dir=$(pwd)

# Lista de arquivos .py para imprimir o nome e o conteúdo
files=(
    "brazbot/bot.py"
    "brazbot/cache.py"
    "brazbot/commands.py"
    "brazbot/decorators.py"
    "brazbot/events.py"
    "brazbot/file.py"
    "brazbot/responses.py"
    "brazbot/utils.py"
    "setup.py"
    "simple_example_interactions.py"
)

# Itera sobre cada arquivo na lista
for file in "${files[@]}"
do
    # Verifica se o arquivo existe
    if [[ -f "$base_dir/$file" ]]; then
        # Imprime o nome do arquivo com ":" no final
        echo "$file:"
        echo
        
        # Imprime o conteúdo do arquivo
        cat "$base_dir/$file"
        echo
        echo
    else
        echo "Arquivo não encontrado: $file"
    fi
done
