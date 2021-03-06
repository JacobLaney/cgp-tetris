from cgp.genome import Genome

from multiprocessing import Pool
from timeit import default_timer as timer
import time
import copy

def run_episode_async(trainer, genome):
    return trainer.run_episode_async(genome)

class TrainingEnvironment:
    OUTPUT_DIR = 'output/'

    def __init__(self):
        self.lastScore = 0

    def run(self, trainer, cgpConfig):
        elite = Genome(cgpConfig)
        bestScore = -1000000
        children = [Genome(cgpConfig) for _ in range(cgpConfig.childrenPerGeneration)]
        env = trainer.get_env()
        for generation in range(cgpConfig.generations):
            startTime = timer()

            elite.update_children(children)

            results = []
            for child in children:
                trainer.reset()
                results.append(trainer.run_episode(env, child))

            for (genome, score) in results:
                if score >= bestScore:
                    bestScore = score
                    genome.copy_into(elite)

            endTime = timer()

            self.log_generation(cgpConfig.modelFile, startTime, endTime, generation, cgpConfig.generations, bestScore)
            elite.save_to_file(cgpConfig.modelFile)

        return (elite, bestScore)

    def run_async(self, trainer, cgpConfig, numProcesses):
        elite = Genome(cgpConfig)
        bestScore = -1000000

        children = [Genome(cgpConfig) for _ in range(cgpConfig.childrenPerGeneration)]
        trainers = [copy.deepcopy(trainer)] * len(children)

        for generation in range(cgpConfig.generations):
            startTime = timer()

            elite.update_children(children)

            pool = Pool(processes=numProcesses, initializer=self.init_pool, initargs=(), maxtasksperchild=1)
            asyncHandles = self.run_children_async(pool, trainers, children)
            results = self.wait(asyncHandles)
            for (genome, score) in results:
                if score >= bestScore:
                    bestScore = score
                    genome.copy_into(elite)
            pool.close()
            pool.join()


            endTime = timer()
            elite.save_to_file(cgpConfig.modelFile)
            self.log_generation(cgpConfig.modelFile, startTime, endTime, generation, cgpConfig.generations, bestScore)

        return (elite, bestScore)

    def init_pool(self):
        pass

    def get_children(self, genome, count):
        return [genome.get_child() for _ in range(count)]

    def run_children_async(self, pool, trainers, children):
        results = []
        for i, _ in enumerate(children):
            trainers[i].reset()
            results.append(pool.apply_async(run_episode_async, args=(trainers[i], children[i])))
        return results

    def wait(self, asyncHandles):
        return [handle.get() for handle in asyncHandles]

    def log_generation(self, modelFile, startTime, endTime, generation, totalGenerations, bestScore):
        timeElapsed = endTime - startTime
        estimatedTimeSec = timeElapsed * (totalGenerations + 1 - generation)
        estimatedTimeMin = estimatedTimeSec / 60.0
        print('Generation ' + str(generation + 1) + ' of ' + str(totalGenerations) + ' complete, current best score = ', bestScore)
        print('Est. minutes remaining: ' + str(estimatedTimeMin))
        with open(modelFile + '.csv', 'a') as f:
            f.write(str(generation))
            f.write(',')
            f.write(str(bestScore))
            f.write(',')
            f.write('\n')
