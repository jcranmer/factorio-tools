'''
This is a library for manipulating factorio data from Python.
'''

import ConfigParser
import factorio_schema
import json
import lupa
import os
import StringIO
import zipfile

# XXX: Fix these for !Linux
FACTORIO_PATH = os.path.join(
    os.path.expanduser("~"), ".steam", "steam", "SteamApps", "common",
    "Factorio")
USER_PATH = os.path.join(os.path.expanduser("~"), ".factorio")

class cached_property(object):
    '''A memoizer for caching getters/setters.'''
    def __init__(self, fget=None):
        if fget is not None:
            self(fget)

    def __call__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, inst, owner):
        try:
            value = inst._cache[self.__name__]
        except (KeyError, AttributeError):
            value = self.fget(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = value
        return value

def add_package_path(lua, path):
    '''Add the directory to the search path in the lua instance.'''
    lua.globals().package.path += ';' + os.path.join(path, '?.lua')

def read_mod_file(moddir, filename):
    '''Load filename from the mod at moddir, which may be a directory or a .zip
    file.'''
    if moddir.endswith('.zip'):
        basename = os.path.basename(moddir)
        filename = os.path.join(basename[:-4], filename)
        with open(moddir) as fd:
            zfd = zipfile.ZipFile(fd)
            with zfd.open(filename) as innerfd:
                return innerfd.read()
    with open(os.path.join(moddir, filename)) as fd:
        return fd.read()

def list_mod_dir(moddir, directory):
    '''Produce a list of files in the directory in the mod.'''
    if moddir.endswith('.zip'):
        basename = os.path.basename(moddir)
        filename = os.path.join(basename[:-4], directory)
        with open(moddir) as fd:
            zfd = zipfile.ZipFile(fd)
            files = zfd.namelist()
        files = map(lambda p: p[len(basename) - 3:], files)
        files = filter(lambda p: p.startswith(directory + '/') and
                p[:-1] != directory, files)
        files = map(lambda p: p[len(directory) + 1:], files)
    else:
        if os.path.exists(os.path.join(moddir, directory)):
            files = os.listdir(os.path.join(moddir, directory))
        else:
            files = []
    return map(lambda p: os.path.join(directory, p), files)

def get_load_order(modmap):
    '''Return a list of mods in the order they need to be loaded in.'''
    # Start by loading the info.json for each file
    infos = dict((mod, json.loads(read_mod_file(f, 'info.json'))) for
        mod, f in modmap.items())

    # Set up the mod list in sort order. Start by eliminating the base mod.
    mods = list(modmap)
    sort_list = ['base']
    mods.remove('base')

    def satisfied_dep(dep):
        pieces = dep.split()
        optional = pieces[0] == '?'
        if optional:
            pieces.pop(0)
            # Optional mods that aren't available to be loaded are satisfied.
            if pieces[0] not in modmap:
                return True
        if len(pieces) == 3:
            if pieces[1] != '>=':
                raise Exception("Unknown dep string: " + dep)
            # XXX: check version?
        return pieces[0] in sort_list

    while len(mods) > 0:
        for mod in mods:
            if 'dependencies' in infos[mod]:
                mod_deps = infos[mod]['dependencies']
                if not all(map(satisfied_dep, mod_deps)):
                    continue
            mods.remove(mod)
            sort_list.append(mod)
    return sort_list

def get_mod_list(factorio_path, mod_path, modlist):
    '''Returns a dict of modname -> mod filename mappings.'''
    # Grab a list of enabled mods
    if modlist is None:
        with open(os.path.join(mod_path, 'mod-list.json')) as fd:
            modlist = json.load(fd)['mods']
            enabled_mods = [d['name'] for d in modlist if d['enabled'] == 'true']
    else:
        enabled_mods = modlist

    # Map the mods to filenames or directories
    possible_files = [os.path.join(mod_path, f) for f in os.listdir(mod_path)]

    # Map modnames to filenames
    modnames = {}
    modnames['base'] = os.path.join(factorio_path, 'data', 'base')
    for path in possible_files:
        base = os.path.basename(path)
        # Strip .zip
        if base.endswith('.zip'): base = base[:-len('.zip')]
        under = base.rfind('_')
        if under < 0: continue
        modnames[base[:under]] = path

    modmap = {}
    for mod in enabled_mods:
        modmap[mod] = modnames[mod]
    return modmap

class FactorioData(object):
    '''This class represents the contextual data for a Factorio data and loaded
    mods.'''
    def __init__(self, path, mod_path, mod_list):
        self.lua = lupa.LuaRuntime(unpack_returned_tuples=True)

        # Load the base modules
        add_package_path(self.lua, os.path.join(path, 'data', 'core', 'lualib'))
        self.lua.require('dataloader')

        # Get the list of mods to use. Note that the base data is itself a
        # module.
        self.mods = get_mod_list(path, mod_path, mod_list)
        load_order = get_load_order(self.mods)

        # We need the core data for a few things, even though it's not listed as
        # a module itself.
        self.mods['core'] = os.path.join(path, 'data', 'core')
        self._load_mod_file('core', 'data')

        # Load modules. Note that the base data is also a module.
        for f in ('data', 'data-updates', 'data-final-fixes'):
            for mod in load_order:
                self._load_mod_file(mod, f)

        # Base Lua data.
        self._data = self.lua.globals().data.raw

    def _lua_search(self, modname):
        ''' This is the loader for the Lua code to be able to load lua files
        from .zip files.'''
        stack = []
        def load_fn(contents):
            val = self.lua.execute(contents)
            stack.pop()
            return val
        def search_fn(filename, retry=True):
            if len(stack):
                context = os.path.dirname(stack[-1])
            if filename.startswith('..'):
                filename = os.path.normpath(os.path.join(context, filename))
            filename = filename.replace('.', '/')
            try:
                contents = read_mod_file(self.mods[modname], filename + '.lua')
            except:
                # Try the last value on the stack?
                if retry and len(stack):
                    val = search_fn(context + '/' + filename, False)
                    if type(val) != type(str):
                        return val
                else:
                    val = ''
                return ("\n\tno file '[%s]/%s.lua'" % (modname, filename)) + val
            stack.append(filename)

            # The searcher checks for a function, so we need to close the actual
            # loading function in a Lua function.
            return self.lua.eval('''
                function (f, str)
                    return function() return f(str) end
                end''')(
                load_fn, contents)

        return search_fn

    def _load_mod_file(self, mod, f):
        '''Load the ${f}.lua file from the mod, if it exists.'''
        directory = self.mods[mod]

        # Add the package searcher for this mod's data
        self.lua.globals().package.searchers[3] = self._lua_search(mod)

        # Undo loaded package info
        for package in self.lua.globals().package.loaded.keys():
            self.lua.globals().package.loaded[package] = False

        #if os.path.exists(os.path.join(directory, f + ".lua")):
        try:
            self.lua.require(f)
        except lupa._lupa.LuaError as e:
            if not e.message.startswith("module '%s' not found:" % f):
                raise

    def load_table(self, table):
        '''Load the given lua table, wrapping each object with the appropriate
        wrapper from the factorio_schema module.'''
        converted = dict()
        if self._data[table] == None:
            print table
        for name, value in self._data[table].items():
            converted[name] = factorio_schema.make_wrapper_object(self, value)
        return converted

    def load_pseudo_table(self, tablename):
        '''Load the set of tables that include objects of the same type as the
        table, wrapped as in load_table.'''
        master_table = dict()
        for table in factorio_schema.get_all_tables(tablename):
            if self._data[table]:
                master_table.update(self.load_table(table))
        return master_table

    def get_l10n_tables(self):
        '''Return a dict of name -> (dict(key -> en(l10n))) values.'''
        master = dict()
        for mod in get_load_order(self.mods):
            moddir = self.mods[mod]
            l10nfiles = list_mod_dir(moddir, 'locale/en')
            l10nfiles = filter(lambda p: p.endswith('.cfg'), l10nfiles)
            for f in l10nfiles:
                parser = ConfigParser.ConfigParser()
                data = read_mod_file(moddir, f)
                data = '[default]\n' + data
                parser.readfp(StringIO.StringIO(data))
                for section in parser.sections():
                    if section not in master:
                        master[section] = dict()
                    master[section].update(parser.items(section))
        return master

    def load_path(self, path):
        '''Returns the contents of the given file.'''
        # The path is __mod__/from/that/file
        mod, subpath = path.split('/', 1)
        assert mod.startswith('__') and mod.endswith('__')
        return read_mod_file(self.mods[mod[2:-2]], subpath)

    def resolve_path(self, name):
        if name is None:
            return ""
        return name.replace('__base__', os.path.join(FACTORIO_PATH, 'data', 'base'))

def load_factorio(path=FACTORIO_PATH, mod_path=os.path.join(USER_PATH, "mods"),
        mod_list=None):
    '''Load the FactorioData for a given path, defaulting to the default Steam
    install location.'''
    return FactorioData(path, mod_path, mod_list)
