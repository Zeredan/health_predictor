package test.task.histories_with_targets.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import test.task.histories_with_targets.HistoriesWithTargetsRepository
import test.task.histories_with_targets.HistoriesWithTargetsRepositoryImpl
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HistoriesWithTargetsRepositoryHiltModule {
    @Binds
    @Singleton
    abstract fun bindHistoriesRepository(historiesRepositoryImpl: HistoriesWithTargetsRepositoryImpl): HistoriesWithTargetsRepository
}