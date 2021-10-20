def normalizedMobile(mobile: str) -> str:
    if mobile[0] == "0":
        return mobile[1:]
    else:
        return mobile
