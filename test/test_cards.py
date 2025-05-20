#
# Test the link card renderer for different variations of links and parsers.
#
# Running this script will generate test_cards-results.html for manual inspection
# and copy/pasting into a Mumble client to inspect how Mumble's HTML renderer
# handles the results.
#
import os
import sys
import traceback

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, os.pardir))
sys.path.insert(0, PROJECT_DIR)

from src.factories import create_card  # nopep8
from tqdm import tqdm  # nopep8


test_cases = [

    # YouTube
    'https://www.youtube.com/watch?v=HvhvfdrxXWo',  # video
    'https://youtu.be/Mx0NLGcL6pI',  # short url
    'https://www.youtube.com/watch?v=aaaaaaaaaaaaaaaaaaaa',  # broken url
    'https://www.youtube.com/watch?v=5qap5aO4i9A',  # live stream
    'https://www.youtube.com/c/OneyPlays/videos',  # profile
    # playlisted video
    'https://www.youtube.com/watch?v=DGOp5CRc8PQ&list=PLIGWVDu9gdfT5YANcIDJ3srlhBrcJC76X',
    # query params are swapped
    'https://www.youtube.com/watch?t=180&v=hklWl7O42do&feature=youtu.be',

    # Vimeo / Misc video platforms
    'https://vimeo.com/638004133',

    # Audio platforms
    'https://soundcloud.com/chuk126/house-hunting-song-adventure?in=user-839869704-138646860/sets/ifk',
    'https://open.spotify.com/track/0kYMwaQWABTkFff8AZjmYI?si=9619a805c81247d2',
    'https://open.spotify.com/album/43KD7ooLIEkXriTaZA4drI?si=bXqew1YpSXq-V_jISuK-6Q',

    # Steam
    'https://steamcommunity.com/sharedfiles/filedetails/?id=2158809703',  # workshop file
    # workshop collection
    'https://steamcommunity.com/sharedfiles/filedetails/?id=2795863638',
    # TTS workshop game
    'https://steamcommunity.com/sharedfiles/filedetails/?id=2799779462&searchtext=',
    'https://steamcommunity.com/id/mcmanning/',  # profile
    'https://store.steampowered.com/app/619150/while_True_learn/',  # game on sale
    # game that will never release
    'https://store.steampowered.com/app/1030300/Hollow_Knight_Silksong/',
    'https://store.steampowered.com/app/1949740/Banana_Shooter/',  # free to play
    'https://store.steampowered.com/app/1288610/Wildcat_Gun_Machine/',  # random game
    # long text in release date
    'https://store.steampowered.com/app/1426870/Dune_Mechanic__Survive_The_Steampunk_Era/',
    # game that will never leave early access
    'https://store.steampowered.com/app/892970/Valheim/',

    # Twitter
    'https://twitter.com/SatisfactoryAF/status/1520043080950427649',  # text post
    'https://twitter.com/deangloster/status/1516998004082761729',  # reply with image
    'https://twitter.com/SatisfactoryAF',  # profile
    # Tweet with a YT video embed
    'https://twitter.com/WoolieWoolz/status/1521220815454412800',
    # Tweet with a steam store embed
    'https://twitter.com/WindybeardGames/status/1521210934248755203',
    # Tweet with 2 images
    'https://twitter.com/FoundInGameMags/status/1521198879294828550?s=20',
    'https://twitter.com/80Level/status/1521074521318567938',  # Tweet with 3 images
    'https://twitter.com/80Level/status/1521051872051703810',  # Another with 3 images
    # Tweet quoting another tweet
    'https://twitter.com/PatStaresAt/status/1521200949259227137',
    'https://twitter.com/KFILE/status/1516945903327891460',  # Tweet with video
    'https://twitter.com/PhantomTheft/status/1521030364164243456',  # Spam tweet

    # Misc
    'https://stackoverflow.com/questions/55333327/extract-meta-keywords-in-python',
    'https://github.com/mumble-voip/mumble/issues/2353',
    'https://open.catalyst.harvard.edu/wiki/display/eaglei/SWEET+Developers\'+Guide',

    # 4chan
    'https://boards.4channel.org/g/thread/76759434',  # thread
    'https://i.4cdn.org/g/1594686780709.png',  # image
    'https://i.4cdn.org/wsg/1650936725126.webm',  # webm (5 MB)
    'https://i.4cdn.org/wsg/1651135239075.webm',  # another webm

    # Reddit
    'https://www.reddit.com/r/DocumentedFights/comments/uicibg/worst_seizure_youll_see_on_any_fight_video_not/',

]


def run_tests():
    successes = 0
    with tqdm(unit='tests', total=len(test_cases)) as progress:
        with open('test_cards-results.html', 'w', encoding='utf-8') as r:
            for url in test_cases:
                r.write('<br/>' + 'Test case: ' + url + '<br/>')
                try:
                    r.write(create_card(url))
                    successes += 1
                except Exception as e:
                    r.write('Failed to generate card: ' + str(e))
                    r.write('<pre>')
                    traceback.print_exc(file=r)
                    r.write('</pre>')

                progress.update(1)

    print("%d/%d successful tests" % (successes, len(test_cases)))


if __name__ == '__main__':
    run_tests()
