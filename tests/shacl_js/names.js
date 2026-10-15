// A SHACL-JS constraint function: every ex:name of the focus node starts upper case.
function hasCapitalisedName($this) {
    var name = TermFactory.namedNode("https://example.org/pyshacl-plugin-test/vocab#name");
    var names = $data.find($this, name, null);
    for (var t = names.next(); t; t = names.next()) {
        var value = t.object.lex;
        if (value.charAt(0) !== value.charAt(0).toUpperCase()) {
            return "Name '" + value + "' does not start with a capital letter";
        }
    }
    return true;
}
