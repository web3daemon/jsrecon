"""jsrecon — map a web app's JavaScript to its API.

Give it a URL or local .js files; it unpacks source maps, parses the code with
tree-sitter, and reports the endpoints, GraphQL operations, routes and config
it can see. For understanding and integrating with APIs you are allowed to use,
and for auditing your own bundles. See README for the intended-use policy.
"""

__version__ = "0.2.0"
