# Author: A01748393 Carlos Garcia Geronis

from arpeggio import PTNodeVisitor


class CodeGenerationVisitor(PTNodeVisitor):

    WAT_TEMPLATE = ''';; Code generated by the Delta compiler
(module
  (func
    (export "_start")
    (result i32)
{}{}  )
)
'''

    def __init__(self, symbol_table, **kwargs):
        super().__init__(**kwargs)
        self.__symbol_table = symbol_table
        self.__label_counter = 0
        self.__label_stack = []

    def visit_program_start(self, node, children):

        def var_decl():
            return ''.join([f'    (local ${var} i32)\n'
                            for var in self.__symbol_table])

        return CodeGenerationVisitor.WAT_TEMPLATE.format(
            var_decl(), ''.join(children))

    def visit_expression_start(self, _, children):
        return CodeGenerationVisitor.WAT_TEMPLATE.format('', children[0])

    def visit_expression(self, _, children):
        if len(children) == 1:
            return children[0]
        result = [children[0]]
        for exp in children[1:]:
            result.append('    if (result i32)\n')
            result.append(exp)
        result.append('    i32.eqz\n' * 2)
        result.append('    else\n'
                      '    i32.const 0\n'
                      '    end\n' * (len(children) - 1))
        return ''.join(result)

    def visit_additive(self, _, children):
        result = [children[0]]
        for i in range(1, len(children), 2):
            result.append(children[i + 1])
            match children[i]:
                case '+':
                    result.append('    i32.add\n')
                case '-':
                    result.append('    i32.sub\n')
        return ''.join(result)

    def visit_multiplication(self, _, children):
        result = [children[0]]
        for i in range(1, len(children), 2):
            result.append(children[i + 1])
            match children[i]:
                case '*':
                    result.append('    i32.mul\n')
                case '/':
                    result.append('    i32.div_s\n')
                case '%':
                    result.append('    i32.rem_s\n')
        return ''.join(result)

    def visit_unary(self, node, children):
        result = children[-1]
        for i in children[-2::-1]:
            match i:
                case '+':
                    ...  # do nothing
                case '-':
                    result = (
                        '    i32.const 0\n'
                        + result
                        + '    i32.sub\n')
                case '!':
                    result += '    i32.eqz\n'
        return result

    def visit_primary(self, _, children):
        return children[0]

    def visit_decimal(self, node, _):
        return f'    i32.const {node.value}\n'

    def visit_boolean(self, _, children):
        if children[0] == 'true':
            return f'    i32.const 1\n'
        else:
            return f'    i32.const 0\n'

    def visit_parenthesis(self, _, children):
        return children[0]

    def visit_rhs_variable(self, node, _):
        return f'    local.get ${node.value}\n'

    def visit_declaration(self, node, _):
        return ''

    def visit_assignment(self, _, children):
        return children[1] + children[0]

    def visit_statement(self, _, children):
        return children[0]

    def visit_lhs_variable(self, node, _):
        return f'    local.set ${node.value}\n'

    def visit_block(self, _, children):
        return ''.join(children)

    def visit_if(self, _, children):
        result = children[0] + '    if\n' + children[1] + '    else\n'
        if len(children) == 3:
            result += children[2]
        result += '    end\n'
        return result

    def visit_while(self, _, children):
        return ('    block\n'
                + '    loop\n'
                + children[0]
                + '    i32.eqz\n'
                + '    br_if 1\n'
                + children[1]
                + '    br 0\n'
                + '    end\n'
                + '    end\n')

    def visit_for(self, node, children):
        loop_var, start, direction, finish, body = children
        if direction == 'upto':
            comparison = '    i32.gt_s\n'
            step = '    i32.add\n'
        else:
            comparison = '    i32.lt_s\n'
            step = '    i32.sub\n'
        return (
            start
            + f'    local.set ${loop_var}\n'
            + '    block\n'
            + '    loop\n'
            + f'    local.get ${loop_var}\n'
            + finish
            + comparison
            + '    br_if 1\n'
            + body
            + f'    local.get ${loop_var}\n'
            + '    i32.const 1\n'
            + step
            + f'    local.set ${loop_var}\n'
            + '    br 0\n'
            + '    end\n'
            + '    end\n')

    def visit_for_variable(self, node, _):
        return node.value

    def visit_loop(self, node, children):
        label = self.__label_stack.pop()
        return (f'    block {label}\n'
                + '    loop\n'
                + children[0]
                + '    br 0\n'
                + '    end\n'
                + '    end\n')

    def visit_loop_start(self, node, children):
        self.__label_stack.append(f'${self.__label_counter:05}')
        self.__label_counter += 1
        return None

    def visit_exit(self, node, children):
        label = self.__label_stack[-1]
        return children[0] + f'    br_if {label}\n'