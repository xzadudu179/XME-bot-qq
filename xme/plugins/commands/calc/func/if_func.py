

def _if(c, t, f):
    from xme.plugins.commands.calc.parser import parse_polynomial
    print(c, t, f)
    return t if bool(parse_polynomial(str(c))[1]) else f

func_name = "if"
func_info = {
    "body": "(c, t, f)",
    "info": "若 c 为 True 则返回 t，否则返回 f",
    "func": _if
}
