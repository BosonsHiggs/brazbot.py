def create_embed(title, description, color=0x5865F2):
    """
    Cria um dicionário de embed para enviar mensagens embutidas no Discord.

    Args:
        title (str): O título do embed.
        description (str): A descrição do embed.
        color (int, opcional): A cor do embed em formato hexadecimal. O padrão é 0x5865F2.

    Returns:
        dict: O dicionário do embed.
    """
    return {
        "title": title,
        "description": description,
        "color": color
    }

def format_command_response(response_text, is_error=False):
    """
    Formata uma resposta de comando com base em se é um erro ou não.

    Args:
        response_text (str): O texto da resposta.
        is_error (bool, opcional): Indica se a resposta é um erro. O padrão é False.

    Returns:
        dict: O dicionário da resposta formatada.
    """
    color = 0xFF0000 if is_error else 0x00FF00
    return create_embed("Resposta do Comando", response_text, color)

def create_error_embed(error_message):
    return {
        "title": "Error",
        "description": error_message,
        "color": 0xFF0000  # Red color for errors
    }