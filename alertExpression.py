'''
Created on 06.09.2014

@author: dk

Grammar:
--------------------------------------------------------------------
BoolExpr       := BoolExpr (OR|XOR) BoolTerm | BoolTerm

BoolTerm       := BoolTerm AND BoolFactor | BoolFactor
            
BoolFactor     := NOT BoolFactor | relExpr | Delay Function

relExpr        := Expr (GT|GE|EQ|NE|LT|LE) Expr | Expr

Expr           := Expr (PLUS|MINUS) Term | Term     # Left associative: a-b-c is (a-b) - c
     
Term           := Term (MUL|DIV) Factor | Factor    # Left associative

Factor         := Constant | NumericVariable | FunctionCall | LPAR Expr RPAR | MINUS Factor

Function       := ValidFunc | SelectFunc | IfFunc

ValidFunc      := (VALID|INVALID) LPAR Parameter RPAR

SelectFunc     := SELECT LPAR ParamList RPAR

ParamList      := ParamList COMMA Parameter
--------------------------------------------------------------------
'''

from bunch import Bunch        

class ExprCompiler():
    '''
    Expression compiler
    '''
    # Lexical Tokens
    EOF         = 0
    COMMA       = 1
    ASSIGN      = 2

    FLOAT_CONST = 3
    INT_CONST   = 4
    BOOL_CONST  = 5
    IDENT       = 6
    REFNUM      = 7

    LEFT_PAR    = 10
    RIGHT_PAR   = 11

    PLUS_OP     = 20
    MINUS_OP    = 21
    MUL_OP      = 22
    DIV_OP      = 23
    UMINUS_OP   = 24
    
    OR_OP       = 30
    XOR_OP      = 31
    AND_OP      = 32
    NOT_OP      = 33

    GT_OP       = 40
    LT_OP       = 41
    GE_OP       = 42
    LE_OP       = 43
    EQ_OP       = 44
    NE_OP       = 45
    
    DELAY_OP    = 50
    
    IF_FUNC     = 80
    SEL_FUNC    = 81
    VALID_FUNC  = 82
    INVALID_FUNC= 83
    DELAY_FUNC  = 84
    ACTIVE_FUNC = 85
    PREV_FUNC   = 86
    
    token2string = {
        ASSIGN:         '=',
        LEFT_PAR:       '(',
        RIGHT_PAR:      ')',
        PLUS_OP:        '+',
        MINUS_OP:       '-',
        UMINUS_OP:      '-',
        MUL_OP:         '*',
        DIV_OP:         '/',
        OR_OP:          '||',
        XOR_OP:         '^^',
        AND_OP:         '&&',
        NOT_OP:         '!',
        GT_OP:          '>',
        LT_OP:          '<',
        GE_OP:          '>=',
        LE_OP:          '<=',
        EQ_OP:          '==',
        NE_OP:          '!=',
        IF_FUNC:        'if',
        SEL_FUNC:       'select',
        VALID_FUNC:     'valid',
        INVALID_FUNC:   'invalid',
        DELAY_FUNC:     'td',
        ACTIVE_FUNC:    'active',
        PREV_FUNC:      'prev'
    }


    # Keywords
    keywords = {
        "if":       IF_FUNC,
        "select":   SEL_FUNC,
        "valid":    VALID_FUNC,
        "inval":    INVALID_FUNC,
        "invalid":  INVALID_FUNC,
        "active":   ACTIVE_FUNC,
        "prev":     PREV_FUNC,
        "td":       DELAY_FUNC,
        "true":     BOOL_CONST,
        "false":    BOOL_CONST,
    }


    INT_TYPE    = 'INT'
    FLOAT_TYPE  = 'FLOAT'
    BOOL_TYPE   = 'BOOL'

    lexdict1 = {
       '=': ASSIGN,
       ',': COMMA,
       '(': LEFT_PAR,
       ')': RIGHT_PAR,
       '+': PLUS_OP,
       '-': MINUS_OP,
       '/': DIV_OP,
       '*': MUL_OP,
       '<': LT_OP,
       '>': GT_OP,
       '!': NOT_OP,
       "'": DELAY_OP,
    }

    lexdict2 = {
       '>=': GE_OP,
       '<=': LE_OP,
       '==': EQ_OP,
       '!=': NE_OP,
       '||': OR_OP,
       '&&': AND_OP,
       '^^': XOR_OP,
    }

    opcodes = {
        (FLOAT_TYPE, PLUS_OP):   ".fadd",
        (FLOAT_TYPE, MINUS_OP):  ".fsub",
        (FLOAT_TYPE, UMINUS_OP): ".fuminus",
        (FLOAT_TYPE, MUL_OP):    ".fmul",
        (FLOAT_TYPE, DIV_OP):    ".fdiv",

        (INT_TYPE,   PLUS_OP):   ".iadd",
        (INT_TYPE,   MINUS_OP):  ".isub",
        (INT_TYPE,   UMINUS_OP): ".iuminus",
        (INT_TYPE,   MUL_OP):    ".imul",
        (INT_TYPE,   DIV_OP):    ".idiv",

        (FLOAT_TYPE, GT_OP):     ".fgt",
        (FLOAT_TYPE, GE_OP):     ".fge",
        (FLOAT_TYPE, LT_OP):     ".flt",
        (FLOAT_TYPE, LE_OP):     ".fle",

        (INT_TYPE, GT_OP):       ".igt",
        (INT_TYPE, GE_OP):       ".ige",
        (INT_TYPE, LT_OP):       ".ilt",
        (INT_TYPE, LE_OP):       ".ile",

        (INT_TYPE, EQ_OP):       ".eq",
        (BOOL_TYPE, EQ_OP):      ".eq",
        (FLOAT_TYPE, EQ_OP):     ".eq",

        (BOOL_TYPE, AND_OP):      ".and",
        (BOOL_TYPE, OR_OP):       ".or",
        (BOOL_TYPE, XOR_OP):      ".xor",
        (BOOL_TYPE, NOT_OP):      ".not",
        
        (FLOAT_TYPE, SEL_FUNC):   ".select",
        (INT_TYPE,  SEL_FUNC):    ".select",
        (BOOL_TYPE, SEL_FUNC):    ".select",

        (FLOAT_TYPE, IF_FUNC):    ".if",
        (INT_TYPE,   IF_FUNC):    ".if",
        (BOOL_TYPE,  IF_FUNC):    ".if",

        (BOOL_TYPE, VALID_FUNC):  ".valid",
        (BOOL_TYPE, INVALID_FUNC):".invalid",
        (INT_TYPE, DELAY_FUNC):   ".td",
        (BOOL_TYPE, ACTIVE_FUNC): ".active",

        (FLOAT_TYPE, PREV_FUNC):   ".prev",
        (INT_TYPE,   PREV_FUNC):   ".prev",
        (BOOL_TYPE,  PREV_FUNC):   ".prev"
    }

    def __init__(self, source, lookupParamFunc, lookupRefnumFunc):
        self.source = source
        self.lookupRefnum = lookupRefnumFunc
        self.lookupParam = lookupParamFunc
        self.postfix = ""
        self.input = source + '\0' # this will be consumed by lexer
        self.pushtokenbuf = []
        
    # --------------------------------------------------------------------------------
    # Lexical Scanner
    # --------------------------------------------------------------------------------
    def gettoken(self):
        '''
        Get next token from input
        returns a token code and a value
        '''
        if len(self.pushtokenbuf):
            #print "poping", self.pushtokenbuf[-1]
            return self.pushtokenbuf.pop()

        # skip space
        while self.input[0].isspace():
            self.input = self.input[1:]
            
        if self.input[0] == '\0':
            return self.EOF, None
        
        if self.input[0].isdigit():
            if self.input.startswith('0x'):
                x = 2;
                while self.input[x].ishexdigit():
                    x = x+1
                value = int(self.input[2:x], 16)
                self.input = self.input[x:]
                return self.INT_CONST, value
            else:
                x = 0
                while self.input[x].isdigit():
                    x = x + 1
                if self.input[x] == "b":
                    # this may be a binary number, otherwise its an syntax error
                    try:
                        value = int(self.input[0:x], 2)
                    except:
                        raise Exception, 'Syntax Error in Expression: Expected Binary Number'
                    token = self.INT_CONST
                    self.input = self.input[x+1:]
                    return token, value
                elif self.input[x] == '.':
                    # should be a floating point number
                    x += 1
                    while self.input[x].isdigit():
                        x = x + 1
                    value = float(self.input[0:x])
                    token = self.FLOAT_CONST
                    self.input = self.input[x:]
                    return token, value
                else:
                    # should be a plain integer 
                    value = self.input[0:x]
                    token = self.INT_CONST
                    self.input = self.input[x:]
                    return token, value
        elif self.lexdict2.has_key(self.input[0:2]):
            token = self.lexdict2[self.input[0:2]]
            self.input = self.input[2:]
            return token, None 
        elif self.lexdict1.has_key(self.input[0]):
            token = self.lexdict1[self.input[0]]
            self.input = self.input[1:]
            return token, None
        # finally this must be an identifier
        elif self.input[0].isalpha() or self.input[0] == '_':
            x = 1
            while self.input[x].isalnum() or self.input[x] == '_':
                x += 1
            value = self.input[0:x]
            # check for keywords
            token = self.keywords.get(value.lower())
            if not token:
                token = self.IDENT
            self.input = self.input[x:]
            return token, value
        else:
            raise Exception, 'Syntax Error in Expression: Unexpected Character: %s' % self.input[0]

    # --------------------------------------------------------------------------------
    def puttoken(self, tok, val):
        '''
        push a token used for look ahead back into the input stream 
        '''
        #print "pushing", tok, val
        self.pushtokenbuf.append((tok, val))

    # --------------------------------------------------------------------------------
    def getrefnum(self):
        '''
        get the stripped string until next ',' or ')'
        This must be a Alert Ref Key
        Used for Active operator wich uses refnum as parameters - which have no defined syntax
        '''
        # skip space
        while self.input[0].isspace():
            self.input = self.input[1:]

        x = 0
        while self.input[x] not in (',', ')', '\0'):
            x += 1
        res = self.input[0:x]

        # consume characters
        self.input = self.input[x:]
        return self.REFNUM, res


    # --------------------------------------------------------------------------------
    def checktoken(self, expectedToken):
        '''
        check if next token is the expected token
        If not, raise exception
        '''
        t, v = self.gettoken()
        if t != expectedToken:
            raise Exception, 'Syntax Error in Expression: Expected "%s"' % self.token2string[expectedToken]
        
    def skipAssign(self):
        '''
        skip the useless 'Out =' at the beginning of the expression
        '''
        self.checktoken(self.IDENT)
        self.checktoken(self.ASSIGN)
        
    # --------------------------------------------------------------------------------
    # Recursive Descend Parser
    # --------------------------------------------------------------------------------
    
    # --------------------------------------------------------------------------------
    def boolExpression(self):
        '''
        boolExpr := boolTerm ( OR|XOR boolTerm )*
        '''
        pf, restype = self.boolTerm()

        token, value = self.gettoken()
        while token in (self.OR_OP, self.XOR_OP):
            pf2, type2 = self.boolTerm()
            if restype == self.BOOL_TYPE and type2 == self.BOOL_TYPE:
                pf += pf2 + [self.opcodes[('BOOL', token)]]
            else:
                raise Exception, 'Type Mismatch in Expression'
            token, value = self.gettoken()
        self.puttoken(token, value)
        return pf, restype

    # --------------------------------------------------------------------------------
    def boolTerm(self):
        '''
        boolTerm := boolFactor ( AND boolFactor )*
        '''
        pf, restype = self.boolFactor()

        token, value = self.gettoken()
        while token == self.AND_OP:
            pf2, type2 = self.boolFactor()
            if restype == self.BOOL_TYPE and type2 == self.BOOL_TYPE:
                pf += pf2 + [self.opcodes[('BOOL', token)]]
            else:
                raise Exception, 'Type Mismatch in Expression'
            token, value = self.gettoken()
        self.puttoken(token, value)
        return pf, restype
                
    
    # --------------------------------------------------------------------------------
    def boolFactor(self):
        '''
        boolFactor := LPAR boolExpr RPAR | boolConst | boolParam | SelectFunc | boolIfFunc 
        '''
        token, value = self.gettoken()
        if token == self.NOT_OP:
            pf, restype = self.boolFactor()
            if restype != self.BOOL_TYPE:
                raise Exception, 'Type Mismatch in Expression: Expect boolean expression after NOT'
            return pf + [self.opcodes[(self.BOOL_TYPE, self.NOT_OP)]], self.BOOL_TYPE
        if token in (self.INT_CONST, self.FLOAT_CONST):
            token2, value2 = self.gettoken()
            if token2 == self.DELAY_OP:
                if token == self.INT_CONST:
                    # Convert integer seconds to number of 100 millisecond cycles
                    iValue = int(float(value) * 10)
                else:
                    # Convert floating point seconds to number of 100 millisecond cycles
                    iValue = int(value * 10.0)

                # handle maximal stupid syntax num ' TD ( bool expr )
                self.checktoken(self.DELAY_FUNC) # Raises exception if wrong
                self.checktoken(self.LEFT_PAR)   # Raises exception if wrong
                pf, restype = self.boolExpression()
                self.checktoken(self.RIGHT_PAR)  # Raises exception if wrong
                return pf + ['.td(%s)' % iValue], restype
            else:
                self.puttoken(token2, value2)
                self.puttoken(token, value)
                return self.relExpression()
        else:
            self.puttoken(token, value)
            return self.relExpression()
        
    # --------------------------------------------------------------------------------
    def relExpression(self):
        '''
        numCompare := numExpr ( COMPAREOP numExpr ) ?
        '''
        def int2bool(pf):
            if len(pf) == 1:
                if   pf[0] == '0':
                    return ['false'], self.BOOL_TYPE
                elif pf[0] == '1':
                    return ['true'], self.BOOL_TYPE
            # its not a 0 or 1, so we have a real type mismatch
            raise Exception, "Type mismatch in expression: Different types for left and right side of compare: %s" % str(pf)
                
        leftpf,  lefttype = self.numExpression()

        token, value = self.gettoken()
        if not token in (self.GT_OP, self.LT_OP, self.GE_OP, self.LE_OP, self.EQ_OP, self.NE_OP):
            self.puttoken(token, value)
            return leftpf, lefttype

        rightpf, righttype = self.numExpression()

        # fix types when we have a comparison between a boolean expr and 0 or 1
        if lefttype == self.BOOL_TYPE and righttype == self.INT_TYPE:
            rightpf, righttype = int2bool(rightpf)
        elif lefttype == self.INT_TYPE and righttype == self.BOOL_TYPE:
            leftpf, lefttype = int2bool(leftpf)

        if lefttype != righttype:
            raise Exception, "Type mismatch in expression: Different types for left and right side of compare"

        if lefttype == self.BOOL_TYPE and token not in (self.EQ_OP, self.NE_OP):
            raise Exception, "Type mismatch in expression: Boolean type for numeric compare"

        # optimize redundant bool == true, bool == false, bool != true, bool != false
        if lefttype == self.BOOL_TYPE and len(rightpf) == 1:
            if token == self.EQ_OP and rightpf[0] == 'true':
                return leftpf, lefttype
            elif token == self.EQ_OP and rightpf[0] == 'false':
                return leftpf + ['.not'], lefttype
            elif token == self.NE_OP and rightpf[0] == 'true':
                return leftpf + ['.not'], lefttype
            elif token == self.NE_OP and rightpf[0] == 'false':
                return leftpf, lefttype

        if token == self.NE_OP: 
            # execution engine does not support NE, so translate to not and eq
            pf =  leftpf + rightpf + [self.opcodes[(lefttype, self.EQ_OP)]]
            pf.append(self.opcodes[(self.BOOL_TYPE, self.NOT_OP)])
        else:
            pf =  leftpf + rightpf + [self.opcodes[(lefttype, token)]]

        return pf, self.BOOL_TYPE
            
                    
    # --------------------------------------------------------------------------------
    def numExpression(self):
        '''
        numExpr := numTerm ( PLUS|MINUS numTerm )*
        '''
        # print "numexpr: input="; self.input, "pushtok=", self.pushtokenbuf
        pf, restype = self.numTerm()

        token, value = self.gettoken()
        while token in (self.PLUS_OP, self.MINUS_OP):
            pf2, type2 = self.numTerm()
            if restype == self.FLOAT_TYPE and type2 == self.FLOAT_TYPE:
                pf += pf2 + [self.opcodes[('FLOAT', token)]]
            elif restype == self.INT_TYPE and type2 == self.INT_TYPE:
                pf += pf2 + [self.opcodes[('INT', token)]]
            else:
                raise Exception, 'Type Mismatch in Expression'
            token, value = self.gettoken()
        self.puttoken(token, value)
        return pf, restype
        
        
    # --------------------------------------------------------------------------------
    def numTerm(self):
        '''
        Term := Factor ( MUL|DIV Factor )*
        '''
        # print "numterm: input="; self.input, "pushtok=", self.pushtokenbuf
        pf, restype = self.numFactor()

        token, value = self.gettoken()
        while token in (self.MUL_OP, self.DIV_OP):
            pf2, type2 = self.numFactor()
            if restype == self.FLOAT_TYPE and type2 == self.FLOAT_TYPE:
                pf += pf2 + [self.opcodes[('FLOAT', token)]]
            elif restype == self.INT_TYPE and type2 == self.INT_TYPE:
                pf += pf2 + [self.opcodes[('INT', token)]]
            else:
                raise Exception, 'Type Mismatch in Expression'
            token, value = self.gettoken()
        self.puttoken(token, value)
        return pf, restype
                
    
    # --------------------------------------------------------------------------------
    def numFactor(self):
        '''
        Factor := LPAR numExpr RPAR | NumConst | NumParam | SelectFunc | IfFunc 
        '''
        # print "numfact: input="; self.input, "pushtok=", self.pushtokenbuf
        token, value = self.gettoken()
        if token == self.LEFT_PAR:
            pf, restype = self.boolExpression()
            self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong
            return pf, restype
        elif token == self.MINUS_OP:
            pf, restype = self.numExpression()
            if restype == self.INT_TYPE or restype == self.FLOAT_TYPE:
                return pf + [self.opcodes[(restype, self.UMINUS_OP)]], restype
            else:
                raise Exception, "Type mismatch in expression"
        elif token == self.INT_CONST:
            return [str(value)], self.INT_TYPE
        elif token == self.FLOAT_CONST:
            return [str(value)], self.FLOAT_TYPE
        elif token == self.BOOL_CONST:
            return [str(value)], self.BOOL_TYPE
        elif token == self.SEL_FUNC:
            self.puttoken(self.SEL_FUNC, "select")
            return self.selectFunction()
            self.checktoken(self.LEFT_PAR)   # Raises exception if wrong
            pf, restype = self.paramList()
            self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong
            if len(pf) == 2:
                return pf + ['.select2'], restype
            elif len(pf) == 3:
                return pf + ['.select3'], restype
            elif len(pf) == 4:
                return pf + ['.select4'], restype
            else:
                raise Exception, "Syntax Error: Bad number of parameters in Select (min=2, max=4)"
            return pf + [self.opcodes[(restype, token)]], restype
        elif token == self.VALID_FUNC or token == self.INVALID_FUNC:
            self.checktoken(self.LEFT_PAR)   # Raises exception if wrong
            pf, restype = self.paramList()
            self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong
            if token == self.VALID_FUNC:
                return ['.valid(%s)' % pf[0]], self.BOOL_TYPE
            else:
                return ['.invalid(%s)' % pf[0]], self.BOOL_TYPE
        elif token == self.PREV_FUNC:
            self.puttoken(token, value)
            return self.prevFunction()
        elif token == self.DELAY_FUNC:
            self.puttoken(self.DELAY_FUNC, "td")
            return self.delayFunction()
        elif token == self.IF_FUNC:
            self.puttoken(token, value)
            return self.ifFunction()
        elif token == self.ACTIVE_FUNC:
            self.puttoken(token, value)
            return self.activeFunction()
        elif token == self.IDENT:
            return self.parameter(value)
        else:
            raise Exception, 'Syntax Error in Expression: Expected Factor'
            
    # --------------------------------------------------------------------------------
    def selectFunction(self):
        self.checktoken(self.SEL_FUNC)   # Raises exception if wrong
        self.checktoken(self.LEFT_PAR)   # Raises exception if wrong
        pf, restype = self.paramList()
        self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong

        # select has two parameters, so we have to transform into multiple selects
        if len(pf) < 2:
            raise Exception, "Syntax Error: Less then 2 parameters in Select"

        opcode = self.opcodes[(restype, self.SEL_FUNC)]
        pfres = pf[0:2] + [opcode]

        for param in pf[2:]:
            pfres += [param, opcode]

        return pfres, restype

    # --------------------------------------------------------------------------------
    def paramList(self):
        '''
        paramList := param ( COMMA param ) *
        '''
        pf, restype = self.parameter()

        token, value = self.gettoken()
        while token == self.COMMA:
            nextpf, nexttype = self.parameter()
            if restype != nexttype:
                raise Exception, "Type mismatch in Expression: SELECT parameters not of same type"
            pf += nextpf 
            token, value = self.gettoken()
        self.puttoken(token, value)
        return pf, restype
        
    # --------------------------------------------------------------------------------
    def parameter(self, value = None):
        '''
        numParam := identifier

        if value is None, get next token
        else IDENT Token is already scanned and value contains the identifier string
        '''
        if value is None:
            token, value = self.gettoken()
            if token != self.IDENT:
                raise Exception, 'Syntax Error in Expression: Expected Parameter'

        name, datatype = self.lookupParam(value)
        return [name], datatype

    # --------------------------------------------------------------------------------
    def activeFunction(self):
        '''
        if value is None, get next refnum token
        else token is already scanned and value contains the refnum string
        '''
        self.checktoken(self.ACTIVE_FUNC)   # Raises exception if wrong
        self.checktoken(self.LEFT_PAR)   # Raises exception if wrong
        numtok, numactive = self.gettoken()
        if numtok != self.INT_CONST:
            raise Exception, 'Syntax Error in Active Function: expected integer '
        
        token, value = self.gettoken()              # Raises exception if wrong
        reflist = []
        while token == self.COMMA:
            tok, ref = self.getrefnum()             # Raises exception if wrong
            val, datatype = self.lookupRefnum(ref)  # Raises exception if not found
            reflist.append(str(val))
            token, value = self.gettoken()          # Raises exception if wrong

        if token != self.RIGHT_PAR:
            raise Exception, 'Syntax Error: Expected ")"'
        
        return reflist + [str(numactive), '.active(%d)' % len(reflist)], self.BOOL_TYPE

    # --------------------------------------------------------------------------------
    def prevFunction(self):
        '''
        prevFunction := LPAR boolExpr | NumParam RPAR
        '''
        self.checktoken(self.PREV_FUNC)  # Raises exception if wrong
        self.checktoken(self.LEFT_PAR)   # Raises exception if wrong

        token, value = self.gettoken()   # Peek at next token
        self.puttoken(token, value)      # Put it back

        if token == self.IDENT:
            # Expected Parameter
            pf, restype = self.parameter()
        else:
            # Expected Boolean expression
            pf, restype = self.boolExpression()

        self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong
        return pf + ['.prev'], restype
        

    # --------------------------------------------------------------------------------
    def ifFunction(self):
        '''
        ifFunction := IF LPAR boolExpr COMMA boolExpr COMMA boolExpr RPAR
        '''
        self.checktoken(self.IF_FUNC)   # Raises exception if wrong
        self.checktoken(self.LEFT_PAR)   # Raises exception if wrong
        condpf, condtype = self.boolExpression()
        if condtype != self.BOOL_TYPE:
            raise Exception, "Type mismatch in IF Function. Expected boolean expression as condition"
        self.checktoken(self.COMMA)   # Raises exception if wrong
        truepf, truetype = self.boolExpression()
        self.checktoken(self.COMMA)   # Raises exception if wrong
        falsepf, falsetype = self.boolExpression()
        self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong
        if truetype != falsetype:
            raise Exception, "Type mismatch in IF Function. True and False expression type different"
        return condpf + truepf + falsepf + ['.if'], truetype

    # --------------------------------------------------------------------------------
    def delayFunction(self):
        '''
        delayFunction := TD LPAR intConst|floatConst COMMA boolExpr RPAR
        '''
        self.checktoken(self.DELAY_FUNC)   # Raises exception if wrong
        self.checktoken(self.LEFT_PAR)     # Raises exception if wrong
        token, value = self.gettoken()

        if token in (self.INT_CONST, self.FLOAT_CONST):
            if token == self.INT_CONST:
                # Convert integer seconds to number of 100 millisecond cycles
                iValue = int(float(value) * 10)
            else:
                # Convert floating point seconds to number of 100 millisecond cycles
                iValue = int(value * 10.0)
        else:
            raise Exception, "Bad parameter to DELAY Function: Expected integer or float constant"

        self.checktoken(self.COMMA)   # Raises exception if wrong
        pf, restype = self.boolExpression()
        if restype != self.BOOL_TYPE:
            raise Exception, "Type mismatch in DELAY Function. Expected boolean expression"
        self.checktoken(self.RIGHT_PAR)   # Raises exception if wrong
        return pf + ['.td(%s)' % iValue], restype
                
def compileToPostfix(source, lkupParam, lkupRefnum):
    '''
    Compile an infix logic expression (in C syntax) into a postfix expression
    Parameters:
        source: expression string to compile
        dd: data dictionary
        ddprefix: prefix to prepend to variables before looking up a name in the DD
    '''

    compiler = ExprCompiler(source, lkupParam, lkupRefnum)
    compiler.skipAssign()

    pfexpr, resulttype = compiler.boolExpression()

    token, value = compiler.gettoken()
    if token != ExprCompiler.EOF:
        raise Exception, "Syntax error in expression: Expected end of expression"
    if resulttype != ExprCompiler.BOOL_TYPE:
        raise Exception, "Type mismatch in expression: Expected boolean result"
    return pfexpr
    


if __name__ == '__main__':

    testdd = {
        'X.a': Bunch(fqname='X.a', datatype='FLOAT'),
        'X.b': Bunch(fqname='X.b', datatype='FLOAT'),
        'X.c': Bunch(fqname='X.c', datatype='FLOAT'),
        'X.d': Bunch(fqname='X.d', datatype='FLOAT'),
        'X.i': Bunch(fqname='X.i', datatype='INT'),
        'X.j': Bunch(fqname='X.j', datatype='INT'),
        'X.t': Bunch(fqname='X.t', datatype='BOOL'),
        'X.f': Bunch(fqname='X.f', datatype='BOOL'),
        'X.FSECU1_Cmd_Slat_Position': Bunch(fqname='X.FSECU1_Cmd_Slat_Position', datatype='FLOAT'),
        'X.FSECU1_Mon_Slat_Position': Bunch(fqname='X.FSECU1_Mon_Slat_Position', datatype='FLOAT'),
        'X.FSECU2_Cmd_Slat_Position': Bunch(fqname='X.FSECU2_Cmd_Slat_Position', datatype='FLOAT'),
        'X.FSECU2_Mon_Slat_Position': Bunch(fqname='X.FSECU2_Mon_Slat_Position', datatype='FLOAT'),
        'X.FSECU1_Cmd_Flap_Position': Bunch(fqname='X.FSECU1_Cmd_Flap_Position', datatype='FLOAT'),
        'X.FSECU1_Mon_Flap_Position': Bunch(fqname='X.FSECU1_Mon_Flap_Position', datatype='FLOAT'),
        'X.FSECU2_Cmd_Flap_Position': Bunch(fqname='X.FSECU1_Mon_Flap_Position', datatype='FLOAT'),
        'X.FSECU2_Mon_Flap_Position': Bunch(fqname='X.FSECU2_Mon_Flap_Position', datatype='FLOAT')
    }
    
    def lkupParam(name):
        p = testdd.get('X.' + name)
        if p:
            return p.fqname, p.datatype
        else:
            raise Exception, "Parameter %s not found in data dictionary" % name
        
    def lkupRefnum(name):
        print '<%s>' % name
        return int(name[-1]), ExprCompiler.INT_TYPE
    
    def testexpr(expr):
        try:
            res = compileToPostfix(expr, lkupParam, lkupRefnum)
            print "%-40s: %s" % (expr, res)
        except Exception, msg:
            print "%-40s: %s" % (expr, msg)

    testexpr("res = t == 1")
    testexpr("res = f == 0")
    testexpr("res = f == 0 + 1")
    testexpr("res = f == 2")

    testexpr("res = active(2, A-1, A-2)")
    testexpr("res = 10'td(a != b)")
    testexpr("res = td(10, a == b)")
    testexpr("res = 2 + 3 == 5")
    testexpr("res = a - b - c == 5.0")
    testexpr("res = 2 + 3 == 5")
    testexpr("res = i / 3 * 2 == 5")
    testexpr("res = (2 == 2 || false) == true")
    testexpr("res = (true || false) == true")
    testexpr("res = 2.5 + 5.0 * 3.0 > 0.0")
    testexpr("res = (5.0) != 0.0")
    testexpr("res = (2.5 + 5.0) * (4.7 - 3.0) != 0.0")
    testexpr("res = 2.5 + 5.0 * (4.7 - 3.0)")
    testexpr("res = true == (5.0 == 7.9)")
    testexpr("res = (true)1 ")
    testexpr("res = 1 == (2 == 3) ")
    testexpr('res = 1 + true')
    testexpr('res = None')
    testexpr('res = a + b')
    testexpr('res = valid(a) || valid(b)')
    testexpr('res = select(a, b)')
    testexpr('res = select(a, b, i)')
    testexpr('res = select(a, b, c)')
    testexpr('res = select(a, b, c, d)')
    testexpr('res = select(i)')
    testexpr('res = select()')
    testexpr('res = if(true, 1, 2)')
    testexpr('res = if(a==b, 1, 2)')
    testexpr('res = if(valid(a), a > 2.0, true)')
    testexpr('res = if(valid(a), a, b) == 0.0')
    testexpr('res = if(valid(a), a, i) == 0')
    testexpr('res = if(valid(a), j+1, i) == 0')
    testexpr('res = if(invalid(a), j+1, i) == 0')
    testexpr('res = if(valid(a), j+1, i) == 0')
    testexpr('res = (20.7<=FSECU1_Cmd_Slat_Position<=21.3)')
    testexpr('res = -5.0 > a')
    testexpr('res = a > -5.0')
    testexpr('res = !(10 == 0111b) && (3 == 9)')
    testexpr('res = !(!(10 == 0111b)) && (3 == 9)')
    testexpr('res = !((10 == 0111b) && (3 == 9))')


    
    
    