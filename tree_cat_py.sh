#!/bin/bash

# Diretório base
base_dir=$(pwd)

# Lista de arquivos .py para imprimir o nome e o conteúdo
files_all=(
    "brazbot/argument_descriptions.py"
    "brazbot/attachments.py"
    "brazbot/audit_log_entry.py"
    "brazbot/autocomplete.py"
    "brazbot/bot_itimized.py"
    "brazbot/bot.py"
    "brazbot/buttons.py"
    "brazbot/cache.py"
    "brazbot/channels.py"
    "brazbot/cogs.py"
    "brazbot/commands.py"
    "brazbot/decorators.py"
    "brazbot/dropdowns.py"
    "brazbot/embed.py"
    "brazbot/events.py"
    "brazbot/eventstype.py"
    "brazbot/file.py"
    "brazbot/forms.py"
    "brazbot/greedy_union.py"
    "brazbot/guilds.py"
    "brazbot/__init__.py"
    "brazbot/literal_arguments.py"
    "brazbot/member.py"
    "brazbot/message_handler.py"
    "brazbot/messages.py"
    "brazbot/optional_arguments.py"
    "brazbot/voiceclient.py"
)

files=(
    "brazbot/bot.py"
    "brazbot/voiceclient.py"
    "example_music_bot.py"
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
done > tree_cat_view.txt
