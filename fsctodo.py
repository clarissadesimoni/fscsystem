from datetime import date
import pyperclip
import MyTodoist
tlist = None
today = date.today()

def createStrings():
    tlist = MyTodoist.getTodoist(MyTodoist.getFile())
    MyTodoist.updateFile(tlist.listTaskIDs())
    projToCat = {
        'University': '1',
        'Personal': '2'
    }
    return list(map(lambda p: f"=td a {projToCat.get(p.name, '3')} {', '.join(list(map(lambda t: t.bullet2 + t.name, p.getUncompletedTasks(False, False))))}", list(filter(lambda pr: len(pr.getUncompletedTasks(False, False)) > 0, tlist.projects.values()))))

def tasklist(clear=True):
    if clear:
        pyperclip.copy('=td')
        input('Checking the old list. Press enter to continue...')
        catToDel = input('Insert the categories to delete (single-spaced): ')
        catToDel = [int(cat) for cat in catToDel.split(' ')]
        while 0 <= len(catToDel) <= 3 and not all(1 <= cat <= 3 for cat in catToDel):
            print('Invalid input.')
            catToDel = input('Insert the categories to delete (single-spaced): ')
        for cat in catToDel:
            pyperclip.copy(f'=td r {cat} all')
            input(f'Deleting tasks fron category {cat}. Press enter to continue...')
    toCopy = createStrings()
    print('There are ' + str(len(toCopy)) + ' categories')
    for s in toCopy:
        pyperclip.copy(s)
        input('Press enter to continue...')
    print('Finished!')

if __name__ == '__main__':
    tasklist(False)