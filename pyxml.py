# # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# pyxml.py  # # # # # # # # # # # # # # # # # # # # # # #
# created by jordan bonecutter  # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # #


class xml_element:
  def __init__(self, name: str, attributes=None, children=None, content='', parent=None):
    if attributes is None:
      attributes = {}
    if children is None:
      children = []
    self.name       = name
    self.attributes = attributes
    self.children   = children
    self.content    = content
    self._parent    = parent


  def __eq__(self, other):
    return self.name == other.name and self.attributes == other.attributes and self.content == other.content


  def dumps(self, indent=''):
    # setup return string
    ret = indent + '<' + self.name

    # add all the attributes
    for attr_name, attr_val in self.attributes.items():
      ret += ' ' + attr_name + '="'
      for c in attr_val:
        if c == '"':
          ret += '\\'
        ret += c
      ret += '"'
    ret += '>'

    # add the indented content
    ret += '\n' + indent
    for c in self.content:
      ret += c
      if c == '\n':
        ret += indent

    # add the children
    for child in self.children:
      ret += child.dumps(indent + '  ')

    ret += indent + '</' + self.name + '>'

    return ret


class xml_tree:
  def __init__(self, root: list, prolog=None):
    self.root = root
    self.prolog = prolog


  def dump(self, fd):
    # write prolog
    if self.prolog is not None:
      fd.write('<?xml')
      for attr_name, attr_val in self.prolog.items(): 
        fd.write(' ' + attr_name + '="') 
        for c in attr_val:
          if c == '"':
            fd.write('\\')
          fd.write(c)
        fd.write('"')
      fd.write('?>\n')

    # write tree
    for child in self.root:
      fd.write(child.dumps())


  @classmethod
  def fromFile(cls, fd):
    '''
    Yes, I know, I know this is prime real estate for recursive logic because
    of the recursive nature of trees. However, I really wanted to do this in a 
    loop with a stack. It was kind of fun. Ok?
    '''
    # get file contents
    data = fd.read()

    # setup read index
    r_i = 0

    # setup root & parent
    root = xml_element('root')
    parent = root

    # setup element stack
    element_stack = []

    # setup prolog
    prolog = {}
    while data[r_i] == ' ' or data[r_i] == '\n' or data[r_i] == '\t':
      r_i += 1

    # check if we are reading in the prolog
    if data[r_i] == '<' and data[r_i + 1] == '?':
      # skip '<?xml'
      r_i += 5

      while True:
        while data[r_i] == ' ' or data[r_i] == '\n' or data[r_i] == '\t':
          r_i += 1
        # end of prolog
        if data[r_i] == '?':
          r_i += 2
          break

        if data[r_i] == '>':
          raise RuntimeError('XML error: prolog must end in ?> not >')

        # read attribute name
        attr_name = ''
        while data[r_i] != ' ' and data[r_i] != '\n' and data[r_i] != '\t' and data[r_i] != '=':
          attr_name += data[r_i] 
          r_i += 1

        # read until value
        if data[r_i] == '=':
          r_i += 1
          while data[r_i].isspace():
            r_i += 1
        else:
          while data[r_i] != '=':
            r_i += 1
          r_i += 1
          while data[r_i].isspace():
            r_i += 1

        # read value
        attr_val = ''
        end      = data[r_i]
        if end != '\'' and end != '"':
          raise RuntimeError('XML Error: xml attributes must be properly escaped strings')
        r_i += 1
        while True:
          if data[r_i] == end:
            if data[r_i - 1] != '\\':
              break
          attr_val += data[r_i] 
          r_i += 1

        prolog[attr_name] = attr_val
        r_i += 1

    # read in the tree
    while True:
      # read in whitespace
      while data[r_i].isspace():
        if r_i == len(data) - 1:
          if len(element_stack) > 0:
            raise RuntimeError('XML error: incomplete xml file')
          return cls(root.children, prolog)
        r_i += 1

      # read element content
      content = ''
      while data[r_i] != '<':
        content += data[r_i]
        r_i += 1
      parent.content += content

      # ignore comments
      if data[r_i+1:r_i+4] == '!--':
        while data[r_i-3:r_i] != '-->':
          r_i += 1
        continue

      #ignore !DOCTYPE
      if data[r_i+1:r_i+9] == '!DOCTYPE':
        qstate = ''
        while True:
          if (data[r_i] == '"' or data[r_i] == '\'') and qstate == '':
            qstate = data[r_i]
          elif qstate != '' and data[r_i] == qstate:
            qstate = ''
          elif data[r_i] == '>' and qstate == '':
            break
          r_i += 1
        continue
  
      # element close
      r_i += 1
      if data[r_i] == '/':
        r_i += 1
        ename = ''
        while data[r_i] != '>':
          ename += data[r_i]
          r_i += 1
        if ename != element_stack[-1]:
          raise RuntimeError('XML err: incorrect closing element at char ' + str(r_i))
        else:
          element_stack.pop()
          parent = parent._parent
          r_i += 1
          continue

      # new element
      # read element name
      ename = ''
      while (not data[r_i].isspace()) and data[r_i] != '/' and data[r_i] != '>':
        ename += data[r_i] 
        r_i += 1
    
      if data[r_i] == '>':
        parent.children.append(xml_element(ename, parent=parent))
        element_stack.append(ename)
        parent = parent.children[-1]
        r_i += 2
        continue
    
      if data[r_i] == '/':
        parent.children.append(xml_element(ename, parent=parent))
        r_i += 2
        continue

      # read element attributes
      attributes = {}
      while True:
        # read whitespace
        while data[r_i].isspace():
          r_i += 1

        # end of attributes
        if data[r_i] == '/':
          parent.children.append(xml_element(ename, attributes, parent=parent))
          r_i += 2
          break
        if data[r_i] == '>':
          parent.children.append(xml_element(ename, attributes, parent=parent))
          element_stack.append(ename)
          parent = parent.children[-1]
          r_i += 1
          break

        # read attribute name
        attr_name = ''
        while (not data[r_i].isspace()) and data[r_i] != '=':
          attr_name += data[r_i] 
          r_i += 1

        # read until value
        if data[r_i] == '=':
          r_i += 1
          while data[r_i].isspace():
            r_i += 1
        else:
          while data[r_i] != '=':
            r_i += 1
          r_i += 1
          while data[r_i].isspace():
            r_i += 1

        # read value
        attr_val = ''
        end      = data[r_i]
        if end != '\'' and end != '"':
          raise RuntimeError('XML Error: xml attributes must be properly escaped strings')
        r_i += 1
        while True:
          if data[r_i] == end:
            if data[r_i - 1] != '\\':
              break
          attr_val += data[r_i] 
          r_i += 1

        attributes[attr_name] = attr_val
        r_i += 1


def main() -> int:
  with open('test2.xml', 'r') as testfile:
    test = xml_tree.fromFile(testfile)
  with open('testout.xml', 'w') as testout:
    test.dump(testout)
  return 0


if __name__ == '__main__':
  main()
