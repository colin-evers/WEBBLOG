import argparse
from flaskblog import create_app
from flask_debugtoolbar import DebugToolbarExtension


app = create_app()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-port", type=int, nargs='?', help="optional position arguement,port assignment, default 5000")
    parser.add_argument("-debug", action='store_true', help="optional switch, debug mode") 
    parser.add_argument("-fdt", action='store_true', help="optional switch, flask debugger toolbar")
    parser.add_argument("-fdt_redirect", action='store_true', help="optional switch, fdt redirects intercepted turned off")
    args = parser.parse_args()
    if args.port:
        #if not specified, will default to 5000
        print ("port assignment:",args.port)
    if args.debug:
        print ("debugger is active")
        app.debug = True
    if args.fdt:
        print ("flask_debugtoolbar turned on")
        app.debug = True
        toolbar = DebugToolbarExtension(app)
        if args.fdt_redirect:
            print ("flask_debugtoolbar redirects turned off")
            app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        else:
            print ("flask_debugtoolbar redirects turned on")
            app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True



    app.run(port=args.port)

    