# =============================================================================
# svelTraverse.py
#
# Tree-walker for svelTest programs: takes an abstract syntax tree and 
# attempts to traverse it to produce the target .py program
# 
# -----------------------------------------------------------------------------
# Columbia University, Spring 2014
# COMS 4115: Programming Languages & Translators, Prof. Aho
#     svelTest team:
#     Emily Hsia, Kaitlin Huben, Josh Lieberman, Chris So, Mandy Swinton
# =============================================================================
import sys;
class SvelTraverse(object):

	def __init__(self, tree, verbose=False):

		# indentation level
		self.level = 0

		# scope level
		self.scope = 0;

		# keep track of variables defined in each scope
		self.scopes = [{}]

		# symbol table (dict)
		self.symbols = {}

		# TODO command line args hack
		self.main_args = []
		self.main_types = []

		# run
		self.code = self.beginning() + self.walk(tree, verbose=verbose) + self.end()

	# --------------
	# helper methods
	# --------------

	def walk(self, tree, flags=None, verbose=False):
		''' call appropriate method based on node type '''
		if isinstance(tree, list):
			for item in tree:
				self.walk(item, flags, verbose)
			return

		method = getattr(self, '_'+tree.type)

		# for type checks that are implemented so far, _method() will return
		# two values [code, _type]. Otherwise, returns one value (just the code)
		returned = method(tree, flags, verbose)
		if isinstance(returned, tuple):
			code, _type = returned
			print "%s: (%s, %s)" % (tree.type, code, _type)
			return code, _type
		else:
			return returned

	def get_code(self):
		return self.code

	def format(self, line = ""):
		''' indent a line according to its level '''
		spaces = 4 * self.level
		return " "*spaces + line

	def level_up(self):
		''' +1 indent; TODO: create new scope '''
		self.level += 1

	def level_down(self):
		''' -1 indent; TODO: remove old scope '''
		self.level -= 1

	def beginning(self):
		imports = "import os, sys\n"
		return imports

	def end(self):
		# extract command line args from main_args
		# and format to int(sys.argv[1]), int(sys.argv[2])
		numOfArgs = len(self.main_args)
		i = 1
		argStr = ""
		while i <= numOfArgs:
			if self.main_types[i-1] == "int":
				argStr += "int(sys.argv[%d]), " % (i)
			elif self.main_types[i-1] == "double":
				argStr += "float(sys.argv[%d]), " % (i)
			else:
				argStr += "sys.argv[%d], " % (i)
			i += 1
		if len(argStr) > 0:
			argStr = argStr[0:-2]
		return "\n\nif __name__ == '__main__':\n\tmain(%s)" % (argStr)

	# --------------------
	# handle grammar nodes
	# --------------------

	# passes testsuite tests 0, 1, 2, 3, 5, 8; works for hello.svel

	# TODO: make sure that we return and are concatenating string types

	def _outer_unit(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: outer_unit"

		return self.walk(tree.children[0], verbose=verbose) + "\n\n" + self.walk(tree.children[1], verbose=verbose)

	def _lang_def(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: lang_def"

		# if lang=Java, copy in java files
		if tree.leaf == "Java":
			jfileutil = open("jfileutil.py").read()
			jfunct = open("jfunct.py").read()
			return jfileutil + "\n\n" + jfunct
		elif tree.leaf == "C":
			cfileutil = open("cfileutil.py").read()
			cfunct = open("cfunct.py").read()
			return cfileutil + "\n\n" + cfunct
		#elif tree.leaf == "Python":
			# implement
		else:
			sys.exit("ERROR: Unrecognized language type.")

	def _translation_unit(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: translation_unit"
		if len(tree.children) == 1:
			return self.walk(tree.children[0], verbose=verbose)
		elif len(tree.children) == 2:
			return self.walk(tree.children[0], verbose=verbose) + "\n\n" + self.walk(tree.children[1], verbose=verbose)

	def _external_declaration(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: external_declaration"

		# -> function_def
		if tree.leaf == None:
			return self.walk(tree.children[0], verbose=verbose)

		# -> type ID SEMICOLON
		if len(tree.children) == 1:
			# add to scope/symbol table
			symbol = tree.leaf
			if not self._symbol_exists(symbol, True):
				_type = self.walk(tree.children[0])
				self._add_scopetable(symbol, True)
				self._add_symtable(symbol, _type, False, True)
			else:
				try:
					raise DuplicateVariableError(symbol)
				except DuplicateVariableError as e:
					print str(e)
			return ""

		# -> type ID ASSIGN assignment_expr SEMICOLON
		else:
			# add to scope/symbol table
			symbol = tree.leaf
			if not self._symbol_exists(symbol, True):
				_type = self.walk(tree.children[0])
				self._add_scopetable(symbol, True)
				self._add_symtable(symbol, _type, True, True)
			else:
				try:
					raise DuplicateVariableError(symbol)
				except DuplicateVariableError as e:
					print str(e)
			return symbol + " = " + self.walk(tree.children[1], verbose)

	# returns code
	def _function_def(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: function_def"

		# TODO: use the format function to do indenting

		# new scope
		self.scope += 1
		print "New scope: " + str(self.scope)
		self.scopes.append({})

		# add to symbol table in GLOBAL scope as ID()
		isMain = False
		if len(tree.children) == 2:
			isMain = True
		functionName = "main"
		if not isMain:
			functionName = tree.leaf
		symbol = functionName + "()" # ID()
		if not self._symbol_exists(symbol, True):
			_type = "void"
			if not isMain:
				_type = tree.children[0].leaf
			self._add_scopetable(symbol, True)
			self._add_symtable(symbol, _type, True, True)
		else:
			try:
				raise DuplicateVariableError(symbol)
			except DuplicateVariableError as e:
				print str(e)

		# -> MAIN LPAREN param_list RPAREN brack_stmt
		if len(tree.children) == 2:
			line = "def main("
			cl_args = self.walk(tree.children[0], flags=["main"], verbose=verbose)
			line += cl_args
			line += "):\n"

			# parse cl_args to insert into generated code
			cl_args = cl_args.split(",")
			for arg in cl_args:
				if arg != '':
					arg = arg.strip()
					self.main_args.append(arg)

			self.level_up()
			line += self.walk(tree.children[1], verbose=verbose)
			self.level_down()

		# -> type ID LPAREN param_list RPAREN brack_stmt
		# -> VOID ID LPAREN param_list RPAREN brack_stmt
		else:
			line = "def "
			line += tree.leaf
			line += "("
			line += self.walk(tree.children[1], verbose=verbose)
			line += "):\n"

			self.level_up()
			line += self.walk(tree.children[2], verbose=verbose)
			self.level_down()

		return line

	# returns code
	def _param_list(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: param_list"

		line = ""

		# -> param_list COMMA parameter
		if len(tree.children) == 2:
			line += self.walk(tree.children[0], flags, verbose=verbose)
			line += ', '
			line += self.walk(tree.children[1], flags, verbose=verbose)

		# -> parameter
		else:
			line += self.walk(tree.children[0], flags, verbose=verbose)

		return line

	# returns code
	def _parameter(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: parameter"

		# TODO command line args hack
		if flags and len(flags) == 1 and flags[0] == "main":
			self.main_types.append(tree.children[0].leaf)

		# -> _empty
		if tree.leaf == None:
			return self.walk(tree.children[0], verbose=verbose)

		# -> type ID
		_type = self.walk(tree.children[0])
		if not self._symbol_exists(tree.leaf):
			self._add_scopetable(tree.leaf) # add to scope table
			self._add_symtable(tree.leaf, _type, True) # add to symbol table

		# put ID in code
		return tree.leaf

	# returns code
	def _empty(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: empty"
		return ""

	# returns code
	def _type(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: type"
		return tree.leaf

	# returns code
	def _brack_stmt(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: brack_stmt"
		return self.walk(tree.children[0], verbose=verbose)

	# returns code
	def _stmts(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: stmts"

		line = ""
		# -> stmts stmt
		if len(tree.children) == 2:
			line += self.walk(tree.children[0], verbose=verbose)
			line += '\n'
			line += self.walk(tree.children[1], verbose=verbose)

		# -> stmt
		# -> brack_stmt
		else:
			line += self.walk(tree.children[0], verbose=verbose)

		return line

	# returns code
	def _stmt(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: stmt"
		return self.format(self.walk(tree.children[0], verbose=verbose))

	# ===========================================================
	# 						Expressions
	# ===========================================================

	def _expression_stmt(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: expression_stmt"

		# -> expression SEMICOLON
		return self.walk(tree.children[0], verbose=verbose)

	def _expression(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: expression"

		# -> type ID
		if tree.leaf:
			symbol = tree.leaf
			_type = self.walk(tree.children[0], verbose=verbose)
			if not self._symbol_exists(symbol):
				self._add_scopetable(symbol)
				self._add_symtable(symbol, _type, False)
			else:
				try:
					raise DuplicateVariableError(symbol)
				except DuplicateVariableError as e:
					print str(e)
			return symbol + " = None" # not sure if this is the best thing to do?

		# -> assignment_expr
		# -> empty
		else:
			return self.walk(tree.children[0], verbose=verbose)

	# This is where we update the scope and symbol tables
	def _assignment_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: assignment_expr"

		# TODO: handle FUNCT!
		# -> logical_OR_expression
		if tree.leaf == None:
			return self.walk(tree.children[0], verbose=verbose)

		# -> FUNCT ID ASSIGN LBRACE funct_name COMMA LPAREN reserved_languages_list RPAREN COMMA primary_expr RBRACE
		elif len(tree.children) == 3:
			# ID check
			if self._symbol_exists(tree.leaf): # if ID already in symbol table
				try:
					raise DuplicateVariableError(tree.leaf)
				except DuplicateVariableError as e:
					print str(e)
			else: # add a new entry in scope and symbol tables
				self._add_scopetable(tree.leaf) # add to scope table
				self._add_symtable(tree.leaf, "funct", True) # add to symbol table

			# -> funct_name verifies string type
			line = tree.leaf + " = Funct(" + self.walk(tree.children[0], verbose=verbose) + \
				", [" + self.walk(tree.children[1], verbose=verbose) + "], "
			
			# type check third argument -- must be file or string type
			returned = self.walk(tree.children[2], verbose=verbose)
			if isinstance(returned, tuple):
				code, _type = returned
				if _type != "ID" and _type != "string":
					try:
						raise TypeMismatchError("funct type's third argument", "file", _type)
					except TypeMismatchError as e:
						print str(e)
				print "assignment_expr: (%s, %s)" % (code, _type)
				line += str(code) + ")"
				return line
			else:
				line += returned + ")"
				return line

		# -> type ID ASSIGN assignment_expr
		# TODO: check if assignment_expr matches with type
		elif len(tree.children) == 2:
			# ID check
			if self._symbol_exists(tree.leaf): # raise exception if ID already in scope/symbol table
				try:
					raise DuplicateVariableError(tree.leaf)
				except DuplicateVariableError as e:
					print str(e)
			else: # add a new entry in scope and symbol tables
				_type = self.walk(tree.children[0], verbose=verbose)
				self._add_scopetable(tree.leaf) # add to scope table
				self._add_symtable(tree.leaf, _type, True) # add to symbol table

			# TODO: do something with the type (symbol table)
			if self.walk(tree.children[0], verbose=verbose) == "file":
				line = "if(not os.path.isfile("
				line += self.walk(tree.children[1], verbose=verbose) + ")):\n"
				
				next_line = "sys.exit('Cannot find "
				self.level_up()
				next_line = self.format(next_line)
				self.level_down()
				next_line += self.walk(tree.children[1], verbose=verbose) + "')\n"

				# this line serves as pseudo-symbol table until we get one
				# TODO: actually use symbol table
				file_name = self.walk(tree.children[1], verbose=verbose)
				janky_line = tree.leaf + "=" + file_name
				janky_line = self.format(janky_line)

				return line + next_line + janky_line + '\n'
			else:
				return tree.leaf + " = " + str(self.walk(tree.children[1], verbose=verbose))

		# -> ID ASSIGN assignment_expr
		# TODO: check if assignment_expr matches with type
		elif len(tree.children) == 1:
			# ID check
			if not self._symbol_exists(tree.leaf): # raise exception if ID not in scope/symbol table
				try:
					raise SymbolNotFoundError(tree.leaf)
				except SymbolNotFoundError as e:
					print str(e)
			else: # type check to see if type of ID matches assignment_expr
				sym_type = self._get_symtable_type(tree.leaf)
				self._update_symtable(tree.leaf) # update symbol table
				#assign_expr_type = self.walk(tree.children[0], verbose=verbose)
				return tree.leaf + " = " + str(self.walk(tree.children[0], verbose=verbose))

		# never reaches
		return self.walk(tree.children[0], verbose=verbose)

	# ===========================================================
	# 					Evaluation expressions
	# ===========================================================

	def _logical_OR_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: logical_OR_expr"

		line = ""

		# logical_OR_expr OR logical_AND_expr
		if len(tree.children) == 2:
			# "boolean", "int", "double", "string"
			# type OR type
			line += str(self.walk(tree.children[0], verbose=verbose))
			line += " or "
			line += str(self.walk(tree.children[1], verbose=verbose))

		# go to logical_AND_expr
		else:
			assert(len(tree.children) == 1)
			line += str(self.walk(tree.children[0], verbose=verbose))

		return line

	def _logical_AND_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: logical_AND_expr"

		line = ""
		if len(tree.children) == 2:
			# logical_AND_expr OR equality_expr
			line += str(self.walk(tree.children[0], verbose=verbose))
			line += " and "
			line += str(self.walk(tree.children[1], verbose=verbose))

		else:
			# go to equality_expr
			assert(len(tree.children) == 1)

			line += str(self.walk(tree.children[0], verbose=verbose))

		return line

	def _equality_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: equality_expr"

		line = ""
		if len(tree.children) == 2:
			# equality_expr EQ/NEQ relational_expr
			line += str(self.walk(tree.children[0], verbose=verbose))
			line += " " + tree.leaf + " "
			line += str(self.walk(tree.children[1], verbose=verbose))

		else:
			# go to relational_expr
			assert(len(tree.children) == 1)

			line += str(self.walk(tree.children[0], verbose=verbose))

		return line

	def _relational_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: relational_expr"

		line = ""
		if len(tree.children) == 2:
			# relational_expr LS_OP/LE_OP/GR_OP/GE_OP additive_expr
			line += str(self.walk(tree.children[0], verbose=verbose))
			line += " " + tree.leaf + " "
			line += str(self.walk(tree.children[1], verbose=verbose))

		else:
			# go to additive_expr
			assert(len(tree.children) == 1)

			line += str(self.walk(tree.children[0], verbose=verbose))

		return line


	def _additive_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: additive_expr"

		line = ""
		if len(tree.children) == 2:
			# additive_expr PLUS/MINUS multiplicative_expr
			line += str(self.walk(tree.children[0], verbose=verbose))
			line += " " + tree.leaf + " "
			line += str(self.walk(tree.children[1], verbose=verbose))

		else:
			# go to multiplicative_expr
			assert(len(tree.children) == 1)

			line += str(self.walk(tree.children[0], verbose=verbose))

		return line

	# WIP returns tuple or code
	def _multiplicative_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: multiplicative_expr"

		line = ""
		# multiplicative_expr TIMES/DIVIDE secondary_expr
		if len(tree.children) == 2:
			mult_type = -1
			secondary_type = -1
			# multiplicative_expr
			r_multiplicative_expr = self.walk(tree.children[0], verbose=verbose)
			if isinstance(r_multiplicative_expr, tuple):
				code, mult_type = r_multiplicative_expr
				print "multiplicative_expr: (%s, %s)" % (code, mult_type)
				line += code
			else:
				print "mult_expr: not implemented 0"
				line += str(r_multiplicative_expr)

			# operator
			line += " " + tree.leaf + " "

			# secondary_expr
			r_secondary_expr = self.walk(tree.children[1], verbose=verbose)
			if isinstance(r_secondary_expr, tuple):
				code, secondary_type = r_secondary_expr
				print "multiplicative_expr: (%s, %s)" % (code, secondary_type)
				line += code
				return line, _type # return tuple
			else:
				print "mult_expr: not implemented 1"
				line += str(r_secondary_expr)

		else:
			# go to multiplicative_expr
			assert(len(tree.children) == 1)
			returned = self.walk(tree.children[0], verbose=verbose)
			if isinstance(returned, tuple):
				return returned
			else:
				print "mult_expr: not implemented 2"
				code = returned
			line += code

		return line

	# return code or tuple
	def _secondary_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: secondary_expr"

		line = ""

		# -> primary_expr
		if tree.leaf == None:
			return self.walk(tree.children[0], verbose=verbose) # returns tuple

		elif tree.leaf == '(':
			# -> LPAREN expression RPAREN
			# -> LPAREN identifier_list RPAREN
			line += '[' + str(self.walk(tree.children[0], verbose=verbose)) + ']'

		elif tree.leaf == '{':
			# -> LBRACE identifier_list RBRACE
			line += '[' + str(self.walk(tree.children[0], verbose=verbose)) + ']'

		return line

	# return code or tuple
	def _primary_expr(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: primary_expr"

		# ID, STRINGLITERAL, NUMBER (INT), DECIMAL (DOUBLE), TRUE/FALSE (BOOLEAN)
		if len(tree.children) == 0:
			_type = self._recognize_type_helper(tree.leaf)
			if _type != "ID":
				return tree.leaf, _type
			# ID : check if ID has been defined for use
			print "_primary_expr: ID"
			symbol = tree.leaf
			if not self._symbol_exists(symbol):
				try:
					raise SymbolNotFoundError(symbol)
				except SymbolNotFoundError as e:
					print str(e)
				_type = "undefined"
			else:
				_type = self._get_symtable_type(symbol)
			return symbol, _type

		# function_call or ref_type
		return self.walk(tree.children[0], verbose=verbose)

	# returns tuple : type or "undefined"
	def _function_call(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: function_call"

		line = ""
		_type = "undefined"

		# -> PRINT LPAREN identifier_list RPAREN
		if tree.leaf == "print":
			code, _type = self.walk(tree.children[0], verbose=verbose)
			if _type == "verbose" or _type == "identifier_list":
				try:
					raise InvalidArguments("print")
				except InvalidArguments as e:
					print str(e)
			_type = "undefined"
			line += tree.leaf + " " + code

		# type conversions
		elif tree.leaf == "string":
			line += "str(" + self.walk(tree.children[0], verbose=verbose) + ")"
			_type = "string"
		elif tree.leaf == "int":
			line += "int(" + self.walk(tree.children[0], verbose=verbose) + ")"
			_type = "int"
		elif tree.leaf == "double":
			line += "float(" + self.walk(tree.children[0], verbose=verbose) + ")"
			_type = "double"
		elif tree.leaf == "boolean":
			line += "bool(" + self.walk(tree.children[0], verbose=verbose) + ")"
			_type = "boolean"
		
		# -> ID PERIOD lib_function LPAREN identifier_list RPAREN
		elif len(tree.children) == 2:
			# TODO: make less hack-y
			function = self.walk(tree.children[0], verbose=verbose)
			if function == "size":
				# TODO (emily): check if id_list is empty
				line += "len(" + tree.leaf + ")"
				_type = "int"
			elif function == "replace":
				args, _id_list_type = self.walk(tree.children[1], verbose=verbose).split(",")
				line += tree.leaf + "[" + args[0].strip() + "] = " + args[1].strip()
				_type = "undefined"
			# TODO: make less hack-y when we have a symbol table
			elif function == "readlines":
				line += "[line.strip() for line in open(%s)]" % (tree.leaf)
				_type = "array"
			elif tree.children[0].leaf == "assert":
				_type = "boolean"
			else:	
				if function == "remove":
					function = "pop"
				code, _id_list_type = self.walk(tree.children[1], verbose=verbose)
				line += tree.leaf + "." + function + "(" + code + ")"
				_type = "undefined"

		# -> ID LPAREN identifier_list RPAREN
		elif len(tree.children) == 1:
			# check if function exists in symbol/scope table
			symbol = tree.leaf + "()"
			_type = "undefined"
			if not self._symbol_exists(symbol, True):
				try:
					raise UndefinedMethodError(tree.leaf)
				except UndefinedMethodError as e:
					print str(e)
				_type = "undefined"
			else:
				_type = self._get_symtable_type(symbol)
				if _type == "void":
					try:
						raise MethodReturnsVoidError(tree.leaf)
					except MethodReturnsVoidError as e:
						print str(e)
					_type = "undefined"
			code, _id_list_type = self.walk(tree.children[0], verbose=verbose)
			if _id_list_type == "verbose":
				try:
					raise InvalidArguments(tree.leaf)
				except InvalidArguments as e:
					print str(e)
			line += tree.leaf + "(" + code + ")"

		return line, _type

	# returns code
	def _lib_function(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: function_call"

		if tree.leaf == "assert":
			# -> ASSERT
			return "_assert"
		elif tree.leaf == "readlines":
			# -> READLINE
			# lines = [line.strip() for line in open(input_file)]
			#line = "[line.strip() for line in open("
			#line += self.walk(tree.children[1], verbose=verbose) + ")]"
			return "readlines"
		else:
			# -> REMOVE | SIZE | INSERT | REPLACE
			return tree.leaf # TODO: will need to do type checking somewhere to make sure this is being called on an array/list

	# returns tuple
	# TODO (emily) : return array type
	def _ref_type(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: ref_type"

		line = ""
		line += self.walk(tree.children[0], verbose=verbose)
		line += '['
		line += str(self.walk(tree.children[1], verbose=verbose))
		line += ']'
		return line, "array"

	def _reserved_languages_list(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: reserved_languages_list"
		
		line = ""
		if len(tree.children) == 1:
			# -> reserved_languages_keyword
			line += "\"" + self.walk(tree.children[0], verbose=verbose) + "\""

		elif len(tree.children) == 2:
			# -> reserved_languages_list COMMA reserved_languages_keyword
			line += self.walk(tree.children[0], verbose=verbose) + ", \"" + self.walk(tree.children[1], verbose=verbose) + "\""

		return line

	def _reserved_languages_keyword(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: reserved_languages_keyword"
		
		if len(tree.children) == 1 and tree.leaf=="*":
			# -> reserved_languages_keyword TIMES
			return self.walk(tree.children[0]) + " " + tree.leaf
		elif isinstance(tree.leaf, basestring):
			# -> RES_LANG LBRACKET RBRACKET
			# -> RES_LANG
			return tree.leaf
		# -> empty
		return self.walk(tree.leaf)

	# returns tuple
	# _type = expression, verbose, identifier_list
	def _identifier_list(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _identifier_list"

		line = ""
		_type = "expression"

		# -> expression
		if len(tree.children) == 1:
			line += str(self.walk(tree.children[0], verbose=verbose))

		# -> identifier_list COMMA VERBOSE
		elif len(tree.children) == 2 and tree.children[1].leaf=="verbose":
			line += str(self.walk(tree.children[0], verbose=verbose)) + ", verbose=True"
			_type = "verbose"

		# -> identifier_list COMMA expression
		elif len(tree.children) == 2:
			line += str(self.walk(tree.children[0], verbose=verbose)) + ", " + str(self.walk(tree.children[1], verbose=verbose))
			_type = "identifier_list"

		return line, _type

	def _ifelse_stmt(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _ifelse_stmt"

		line = ""
		if len(tree.children) == 2:
			# if
			line += "if "
			line += self.walk(tree.children[0], verbose=verbose)
			line += ":\n"

			self.level_up()
			line += self.walk(tree.children[1], verbose=verbose)
			self.level_down()

		elif len(tree.children) == 3:
			# if-else
			line += "if "
			line += self.walk(tree.children[0], verbose=verbose)
			line += ":\n"

			self.level_up()
			line += self.walk(tree.children[1], verbose=verbose) + "\n"
			self.level_down()

			# need to format this line since it's not the beginning of the stmt
			line += self.format("else:\n")

			self.level_up()
			line += self.walk(tree.children[2], verbose=verbose)
			self.level_down()

		return line

	def _loop_stmt(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _loop_stmt"

		line = ""
		if len(tree.children) == 2:
			# while
			line += "while "
			line += self.walk(tree.children[0], verbose=verbose)
			line += ":\n"

			self.level_up()
			line += self.walk(tree.children[1], verbose=verbose)
			self.level_down()

		elif len(tree.children) == 4:
			# for TODO: refactor -- very hack-y atm
			line += self.walk(tree.children[0], verbose=verbose) + '\n'
			line += self.format("while ")
			line += self.walk(tree.children[1], verbose=verbose)
			line += ":\n"

			self.level_up()
			# TODO: insert statements inside the for loop
			line += self.walk(tree.children[3], verbose=verbose) + '\n'
			line += self.format(self.walk(tree.children[2], verbose=verbose))
			self.level_down()

		return line

	def _jump_stmt(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _jump_stmt"

		line = ""
		if tree.leaf == 'break':
			line = tree.leaf

		elif tree.leaf == 'continue':
			line = tree.leaf

		elif tree.leaf == 'return':
			line += "return "
			line += self.walk(tree.children[0], verbose=verbose)

		return line


	'''
	@return code
	@raise TypeMismatchError
	'''
	def _funct_name(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _funct_name"

		# -> __MAIN__
		if tree.leaf == "__main__":
			return "\"main\""

		# -> primary_expr
		returned = self.walk(tree.leaf, verbose=verbose)
		if isinstance(returned, tuple):
			code, _type = returned
			print "_funct_name: (%s, %s)" % (code, _type)
			if _type != "ID" and _type != "string":
				try:
					raise TypeMismatchError("funct first argument", "string", _type)
				except TypeMismatchError as e:
					print str(e)
			return code
		else:
			return returned

	def _STRINGLITERAL(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _STRINGLITERAL"
		return tree.leaf

	def _ID(self, tree, flags=None, verbose=False):
		if(verbose):
			print "===> svelTraverse: _ID"
		return tree.leaf

	#################################################################################
	#						 Type checking helper functions 						#
	#################################################################################
		'''
        no type means --> case 2
        no value means --> case 0
        both means --> case 1

        case 0: declaration of new variable (just type, no value)
            int x;
        case 1: declaration of new variable and assignment of value (DEFAULT VAL?)
            int x = 0; (x doesn't exist yet)
            int x = 0; (x already exists --> new scope or throw error)
        case 2: assignment of value to existing variable (value may or may not have existed)
            x = 0; (x in symbol table)
            x = 0; (x not in symbol table --> throw error)
        '''

	''' Check if symbol exists in the current scope and global scope '''
	def _symbol_exists(self, symbol, isGlobal=False):
		# check if exists in global
		if symbol in self.scopes[0]:
			return True
		# check if exists in current scope
		if not isGlobal:
			if symbol in self.scopes[self.scope]:
				return True
		return False

	''' Add symbol to scope table '''
	def _add_scopetable(self, symbol, isGlobal=False):
		if isGlobal:
			self.scopes[0][symbol] = True
		else:
			self.scopes[self.scope][symbol] = True
		print "Added %s to the scope table: %s" % (symbol, str(self.scopes))

	''' Add symbol to symbol table '''
	def _add_symtable(self, symbol, _type, hasValue, isGlobal=False):
		entry = self._get_symtable_entry(symbol, isGlobal)
		self.symbols[entry] = [_type, hasValue]
		print "Added %s to the symbol table: %s" % (symbol, str(self.symbols))
		return entry

	''' Update symbol in symbol table '''
	def _update_symtable(self, symbol, _type, hasValue):
		entry = self._get_symtable_entry(symbol)
		self.symbols[entry][1] = True
		return entry

	'''Returns the entry in the symbol table dictionary'''
	def _get_symtable_entry(self, symbol, isGlobal=False):
		if isGlobal:
			return str(0) + str(symbol)
		return str(self.scope) + str(symbol)

	''' Returns the type of the symbol recorded by the symbol table '''
	def _get_symtable_type(self, symbol, isGlobal=False):
		entry = self._get_symtable_entry(symbol, isGlobal)
		return self.symbols[entry][0]

	''' Recognize the type of a primary_expr '''
	def _recognize_type_helper(self, primary_expr):
		if self._is_boolean(primary_expr):
			return "boolean"
		if self._is_int(primary_expr):
			return "int"
		if self._is_float(primary_expr):
			return "float"
		if self._is_string(primary_expr):
			return "string"
		return "ID"

	def _is_boolean(self, primary_expr):
		return primary_expr == "true" or primary_expr == "false"

	# always check _is_int() before checking _is_float()
	def _is_int(self, primary_expr):
		try:
			a = float(primary_expr)
			b = int(a)
		except ValueError:
			return False
		else:
			return a == b

	# always check _is_int() before checking _is_float()
	def _is_float(self, primary_expr):
		try:
			a = float(primary_expr)
		except ValueError:
			return False
		return True

	def _is_string(self, primary_expr):
		if "\"" in primary_expr:
			return True
		return False

#################################################################################
#					  svelTest defined Exceptions 								#
#################################################################################
class TypeMismatchError(Exception):
	def __init__(self, context, expected, actual):
		self.context = context
		self.expected = expected
		self.actual = actual
	def __str__(self):
		return "TypeMismatchError : %s requires %s type. Found %s." % \
				(self.context, self.expected, self.actual)

class DuplicateVariableError(Exception):
	def __init__(self, var):
		self.var = var
	def __str__(self):
		return "DuplicateVariableError : symbol %s already defined." % (self.var)

class SymbolNotFoundError(Exception):
	def __init__(self, var):
		self.var = var
	def __str__(self):
		return "SymbolNotFoundError : cannot find symbol %s." % (self.var)

class UndefinedMethodError(Exception):
	def __init__(self, method):
		self.method = method
	def __str__(self):
		return "UndefinedMethodError : method %s not defined." (self.method)

class OperatorCannotBeApplied(Exception):
	def __init__(self, operator, type_1, type_2):
		self.operator = operator
		self.type_1 = type_1
		self.type_2 = type_2
	def __str__(self):
		return "Operator %s cannot be applied to types %s, %s." % (self.operator, self.type_1, self.type_2)

class InvalidArguments(Exception):
	def __init__(self, function):
		self.function = function
	def __str__(self):
		return "Invalid arguments for %s()" % (self.function)

class UnexpectedSymbol(Exception):
	def __init__(self, symbol):
		self.symbol = symbol
	def __str__(self):
		return "Unexpected symbol : %s." % (self.symbol)

class MethodReturnsVoidError(Exception):
	def __init__(self, method):
		self.method = method
	def __str__(self):
		return "VoidError : method %s returns void" % (self.method)