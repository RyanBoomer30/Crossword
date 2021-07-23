import sys

from crossword import *
import copy
import random


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """

        # Create a deepcopy for iteration
        placeholder = copy.deepcopy(self.domains)

        # Iterate through all domain variables
        for i in self.domains:
            for j in placeholder[i]:

                # Remove any value that doesn't have appropriate length
                if len(j) != i.length:
                    self.domains[i].remove(j)
        print (self.domains)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps[x, y]
        placeholder = copy.deepcopy(self.domains[x])

        if overlap is not None:
            i = overlap[0]
            j = overlap[1]
            
            count = 0

            for x_domain in placeholder:
                for y_domain in self.domains[y]:
                    if x_domain[i] == y_domain[j]:
                        count += 1

                # The two domains are not consistent
                # Remove the "bad" elements
                if count == 0:      
                    self.domains[x].remove(x_domain)
                    revised = True
            
        return revised 

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        # Start with all of the arcs in the problem
        if arcs is None:
            queue = []
            for i in self.domains.keys():
                for j in self.domains.keys():
                    if i != j:
                        queue.append((i,j))
        else:
            queue = arcs

        while queue:
            # Dequeue
            arc = queue.pop(0)
            i = arc[0]
            j = arc[1]

            # Make sure the arcs are consistent
            if self.revise(i, j):

                if(self.domains[i] is None):
                    return False
                else:
                    # Enqueue all arcs (i_neighbor, i) (where i_neighbor is all neighbors except j)
                    for i_neighbor in self.crossword.neighbors(i):
                        if i_neighbor != j:
                            queue.append((i_neighbor, i))
        
        return True


    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for i in self.domains.keys():
            if i not in assignment.keys():
                return False
            elif assignment[i] is None:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for key, value in assignment.items():
            # Check if all values are distinct
            # https://thispointer.com/python-3-ways-to-check-if-there-are-duplicates-in-a-list/
            if len(assignment.values()) != len(set(assignment.values())):
                return False 
            
            # Check if all values have the same correct length
            if (key.length != len(value)):
                return False

            # Check conflicts between neighboring variables
            for neighbors in self.crossword.neighbors(key):
                overlap = self.crossword.overlaps[key,neighbors]
                i = overlap[0]
                j = overlap[1]
                if neighbors in assignment:
                    if value[i] != assignment[neighbors][j]:
                        return False
        return True
        
    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        variables = self.domains[var]
        neighbors = self.crossword.neighbors(var)
        result = {}

        for i in variables:
            # Pick out values' constraining values heuristic
            if i not in assignment:
                count = 0
                for j in neighbors:
                    if i in self.domains[j]:
                        count += 1
                result[i] = count      

        return sorted(result, key=lambda key: result[key])
        

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        variable = None
        highest_length = 0

        for i in self.domains:
            if i not in assignment:
                # Keep track of the varible with the fewest domain values
                if len(self.domains[i]) < highest_length or highest_length == 0:
                    variable = i
                    highest_length = len(self.domains[i])
                elif len(self.domains[i]) == highest_length:
                    # Keep track of the varible with the most neighbors
                    if len(self.crossword.neighbors(i)) > len(self.crossword.neighbors(variable)):
                        variable = i
                    # If tie, decide a word randomly
                    elif len(self.crossword.neighbors(i)) == len(self.crossword.neighbors(variable)):
                        if random.random() <= 0.5:
                            variable = i
        return variable

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # Check if everything is filled
        if self.assignment_complete(assignment):
            return assignment

        # Get the next variable
        next_variable = self.select_unassigned_variable(assignment)
        
        # Recursively run backtrack until received a valid result
        for i in self.order_domain_values(next_variable, assignment):
            assignment[next_variable] = i
            if self.consistent(assignment) == False:
                assignment.pop(next_variable)
                continue
            result = self.backtrack(assignment)
            if result:
                return result
            assignment.pop(next_variable)
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
