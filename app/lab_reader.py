"""FM27 Tactics Lab save reader: turns a Football Manager save into the Lab's squad JSON.
Runs in Pyodide in the browser. Built on fmsave (MIT, (c) Randal S. Olson)."""
import json, warnings, gc, dataclasses
import fmsave

ATTR = {'crossing':'Cro','dribbling':'Dri','finishing':'Fin','first_touch':'Fir','heading':'Hea','long_shots':'Lon',
 'marking':'Mar','passing':'Pas','tackling':'Tck','technique':'Tec','aggression':'Agg','anticipation':'Ant','bravery':'Bra',
 'composure':'Cmp','concentration':'Cnt','decisions':'Dec','determination':'Det','flair':'Fla','off_the_ball':'OtB',
 'positioning':'Pos','teamwork':'Tea','vision':'Vis','work_rate':'Wor','acceleration':'Acc','agility':'Agi','balance':'Bal',
 'jumping_reach':'Jum','pace':'Pac','stamina':'Sta','strength':'Str','aerial_reach':'Aer','command_of_area':'Cmd',
 'communication':'Com','handling':'Han','kicking':'Kic','one_on_ones':'1v1','reflexes':'Ref','rushing_out':'Rus'}
RATING_KEYS = ('gk','sw','dl','dc','dr','dm','ml','mc','mr','aml','amc','amr','stc','wbl','wbr')
_state = {}

def _num(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return v if 1 <= v <= 20 else None

def _player(p, cuid):
    a = p.attributes
    attrs = {}
    if a is not None:
        for f, k in ATTR.items():
            v = _num(getattr(a, f, None))
            if v is not None: attrs[k] = v
    ratings = {}
    if p.positions is not None:
        for k in RATING_KEYS:
            v = getattr(p.positions, k, None)
            if isinstance(v, int): ratings[k] = v
    ab = p.ability
    return {'uid': str(p.unique_id or p.uid), 'name': p.name, 'age': p.age,
            'ratings': ratings, 'attrs': attrs,
            'ca': getattr(ab, 'current', None) if ab else None,
            'pa': getattr(ab, 'potential', None) if ab else None,
            'club': p.club_name, 'mine': cuid is not None and p.club_uid == cuid,
            'loan': bool(p.on_loan)}

def read(path, scope='squad'):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        save = fmsave.open(path)
        try:
            info = save.info
            try:
                managed = save.managed_clubs()
            except fmsave.FmsaveError:
                managed = ()
            club = managed[0] if managed else None
            cuid = club.club_uid if club else None
            table = save.players().filter(lambda p: bool(p.name))
            if scope == 'squad' and cuid is not None:
                rows = [p for p in table if p.club_uid == cuid or getattr(p, 'loan_parent_club_uid', None) == cuid]
            else:
                rows = list(table)
            out = {'game': info.game, 'build': info.build, 'save': info.save_name,
                   'date': None if info.game_date is None else info.game_date.isoformat(),
                   'club': club.club_name if club else None, 'total': len(table),
                   'players': [_player(p, cuid) for p in rows]}
        finally:
            try: save.close()
            except Exception: pass
    gc.collect()
    return json.dumps(out)

def safe_read(path, scope='squad'):
    try:
        return read(path, scope)
    except fmsave.NotAFmSaveError:
        msg = "That file isn't a Football Manager save. Pick a .fm file from your games folder."
    except fmsave.UnsupportedGameError:
        msg = "This save is from an FM build the reader doesn't support yet."
    except fmsave.CorruptSaveError:
        msg = "This save looks damaged or incomplete. Try a fresh copy."
    except fmsave.SaveChangedError:
        msg = "The save changed while being read. Wait for FM to finish saving."
    except fmsave.FmsaveError as e:
        msg = "The reader couldn't read this save (%s)." % type(e).__name__
    except MemoryError:
        msg = "Ran out of memory reading this save. Close other tabs and try again."
    return json.dumps({'error': msg})
