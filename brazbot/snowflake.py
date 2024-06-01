class Snowflake:
    """
    TODO:
    A "snowflake" in the context of the Discord API is a unique identifier that 
    represents objects within the platform, such as users, messages, channels, etc. 
    This identifier is a 64-bit number, and contains information about when the object was created.
    """
    @staticmethod
    def is_valid(snowflake):
        try:
            int_snowflake = int(snowflake)
            return int_snowflake > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def parse(snowflake):
        if Snowflake.is_valid(snowflake):
            return int(snowflake)
        else:
            raise ValueError(f"Invalid snowflake value: {snowflake}")
